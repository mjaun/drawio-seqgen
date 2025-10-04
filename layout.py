from dataclasses import dataclass
from typing import List, Dict, Optional, Set

import seqast
import drawio

LIFELINE_DEFAULT_WIDTH = 160
LIFELINE_DEFAULT_SPACING = 40
LIFELINE_HEIGHT = 40

TITLE_FRAME_PADDING = 30

CONTROL_FRAME_BOX_WIDTH = 60
CONTROL_FRAME_BOX_HEIGHT = 20
CONTROL_FRAME_SPACING = 20

STATEMENT_OFFSET_Y = 10
MESSAGE_MIN_SPACING = 20

ACTIVATION_STACK_OFFSET_X = drawio.ACTIVATION_WIDTH / 2


class ParticipantInfo:
    def __init__(self, index: int, lifeline: drawio.Lifeline):
        self.index = index
        self.lifeline = lifeline
        self.activation_stack: List[drawio.Activation] = []


class FrameInfo:
    def __init__(self, frame: drawio.Frame):
        self.frame = frame
        self.participants: Set[ParticipantInfo] = set()
        self.inner_frames: Set[FrameInfo] = set()


class Layouter:
    def __init__(self, description: seqast.SeqDescription):
        self.description = description
        self.participant_info: Dict[str, ParticipantInfo] = {}
        self.last_offset_per_gap: Dict[int, int] = {i: 0 for i in range(len(description.participants) - 1)}
        self.frame_stack: List[FrameInfo] = []
        self.current_position_y = LIFELINE_HEIGHT + (2 * STATEMENT_OFFSET_Y)

        self.file = drawio.File()
        self.page = drawio.Page(self.file, 'Diagram')
        self.title_frame = drawio.Frame(self.page, '')

        self.executed = False

    def layout(self) -> drawio.File:
        assert not self.executed, "layouter instance can only be used once"
        self.executed = True

        self.setup_participants()
        self.setup_title_frame()

        self.process_statements(self.description.statements)

        self.finalize_participants()
        self.finalize_title_frame()

        return self.file

    def setup_participants(self):
        lifeline_width = LIFELINE_DEFAULT_WIDTH
        lifeline_spacing = LIFELINE_DEFAULT_SPACING
        end_x = 0

        for index, declaration in enumerate(self.description.participants):
            if isinstance(declaration, seqast.ParticipantNameDeclaration):
                lifeline = drawio.Lifeline(self.page, declaration.text)
                lifeline.x = end_x + lifeline_spacing if end_x else 0
                lifeline.width = lifeline_width
                lifeline.height = LIFELINE_HEIGHT
                end_x = lifeline_width + lifeline.x

                self.participant_info[declaration.name] = ParticipantInfo(index, lifeline)

            elif isinstance(declaration, seqast.ParticipantWidthDeclaration):
                lifeline_width = declaration.width

            elif isinstance(declaration, seqast.ParticipantSpacingDeclaration):
                lifeline_spacing = declaration.spacing

            else:
                raise NotImplementedError()

    def setup_title_frame(self):
        if title_decl := self.description.title:
            self.title_frame.value = title_decl.text
        else:
            self.title_frame.value = 'Sequence Diagram'

        if title_size_decl := self.description.title_size:
            self.title_frame.box_width = title_size_decl.width
            self.title_frame.box_height = title_size_decl.height

        self.title_frame.x = -TITLE_FRAME_PADDING
        self.title_frame.y = -TITLE_FRAME_PADDING - self.title_frame.box_height

        participants_width = max(p.lifeline.x + p.lifeline.width for p in self.participant_info.values())
        self.title_frame.width = participants_width + (2 * TITLE_FRAME_PADDING)

    def finalize_participants(self):
        self.current_position_y += (2 * STATEMENT_OFFSET_Y)

        for participant in self.participant_info.values():
            assert not participant.activation_stack, "participants must be inactive at end"
            participant.lifeline.height = self.current_position_y

    def finalize_title_frame(self):
        self.title_frame.height = (self.current_position_y - self.title_frame.y) + TITLE_FRAME_PADDING

    def process_statements(self, statements: List[seqast.Statement]):
        handlers = {
            seqast.ActivateStatement: self.handle_activate,
            seqast.DeactivateStatement: self.handle_deactivate,
            seqast.MessageStatement: self.handle_message,
            seqast.SelfCallStatement: self.handle_self_call,
            seqast.SpacingStatement: self.handle_spacing,
            seqast.OptionStatement: self.handle_option,
        }

        for statement in statements:
            # noinspection PyTypeChecker
            handlers[type(statement)](statement)

    def handle_activate(self, statement: seqast.ActivateStatement):
        participant = self.participant_info[statement.name]

        self.activate_participant(participant)
        self.add_frame_participants(participant)
        self.current_position_y += STATEMENT_OFFSET_Y

    def handle_deactivate(self, statement: seqast.DeactivateStatement):
        participant = self.participant_info[statement.name]
        assert participant.activation_stack, "deactivation not possible, participant is inactive"

        self.deactivate_participant(participant)
        self.add_frame_participants(participant)
        self.current_position_y += STATEMENT_OFFSET_Y

    def handle_message(self, statement: seqast.MessageStatement):
        assert statement.sender != statement.receiver, "use self call syntax"

        handlers = {
            seqast.MessageActivationType.REGULAR: self.handle_message_regular,
            seqast.MessageActivationType.ACTIVATE: self.handle_message_activate,
            seqast.MessageActivationType.DEACTIVATE: self.handle_message_deactivate,
            seqast.MessageActivationType.FIREFORGET: self.handle_message_fireforget,
        }

        # noinspection PyArgumentList
        handlers[statement.activation](statement)

    def handle_message_regular(self, statement: seqast.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"
        assert receiver.activation_stack, "receiver must be active to receive a message"

        self.ensure_message_spacing(sender, receiver, 0)
        message = self.create_message(sender, receiver, statement)

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_position_y
        ))

        self.add_frame_participants(sender, receiver)
        self.current_position_y += STATEMENT_OFFSET_Y

    def handle_message_activate(self, statement: seqast.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"

        self.ensure_message_spacing(sender, receiver, drawio.MESSAGE_ANCHOR_DY)
        self.activate_participant(receiver, sender)
        message = self.create_message(sender, receiver, statement)

        if sender.index < receiver.index:
            message.type = drawio.MessageAnchor.TOP_LEFT
        else:
            message.type = drawio.MessageAnchor.TOP_RIGHT

        self.add_frame_participants(sender, receiver)
        self.current_position_y += STATEMENT_OFFSET_Y

    def handle_message_deactivate(self, statement: seqast.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"
        assert receiver.activation_stack, "deactivation not possible, participant is inactive"

        self.ensure_message_spacing(sender, receiver, -drawio.MESSAGE_ANCHOR_DY)
        message = self.create_message(sender, receiver, statement)

        if sender.index < receiver.index:
            message.type = drawio.MessageAnchor.BOTTOM_RIGHT
        else:
            message.type = drawio.MessageAnchor.BOTTOM_LEFT

        self.deactivate_participant(sender)

        self.add_frame_participants(sender, receiver)
        self.current_position_y += STATEMENT_OFFSET_Y

    def handle_message_fireforget(self, statement: seqast.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"

        self.activate_participant(receiver, sender)
        self.current_position_y += STATEMENT_OFFSET_Y

        self.ensure_message_spacing(sender, receiver, STATEMENT_OFFSET_Y)
        message = self.create_message(sender, receiver, statement)

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_position_y
        ))

        self.current_position_y += STATEMENT_OFFSET_Y
        self.deactivate_participant(receiver)

        self.add_frame_participants(sender, receiver)
        self.current_position_y += STATEMENT_OFFSET_Y

    def handle_self_call(self, statement: seqast.SelfCallStatement):
        participant = self.participant_info[statement.name]

        assert participant.activation_stack, "participant must be active for self call"

        # create activation for self call
        self.current_position_y += STATEMENT_OFFSET_Y
        self.activate_participant(participant)

        # create self call message
        regular_activation = participant.activation_stack[-2]
        self_call_activation = participant.activation_stack[-1]
        message = drawio.Message(regular_activation, self_call_activation, statement.text)
        message.alignment = drawio.TextAlignment.MIDDLE_RIGHT

        self_call_x = participant.lifeline.center_x() + self_call_activation.dx + 25

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_position_y - STATEMENT_OFFSET_Y,
        ))

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_position_y + STATEMENT_OFFSET_Y,
        ))

        # deactivate after self call
        self.current_position_y += 2 * STATEMENT_OFFSET_Y
        self.deactivate_participant(participant)

        self.add_frame_participants(participant)
        self.current_position_y += STATEMENT_OFFSET_Y

    def handle_option(self, statement: seqast.OptionStatement):
        # create frame
        self.current_position_y += STATEMENT_OFFSET_Y

        frame = drawio.Frame(self.page, 'opt')
        frame.y = self.current_position_y
        frame.box_width = CONTROL_FRAME_BOX_WIDTH
        frame.box_height = CONTROL_FRAME_BOX_HEIGHT

        # push frame stack
        frame_info = FrameInfo(frame)

        if self.frame_stack:
            self.frame_stack[-1].inner_frames.add(frame_info)

        self.frame_stack.append(frame_info)

        # positioning on frame begin
        self.current_position_y += CONTROL_FRAME_BOX_HEIGHT
        self.reset_offset_per_gap()
        self.current_position_y += STATEMENT_OFFSET_Y

        # process inner statements
        self.process_statements(statement.inner)

        # set frame height
        self.current_position_y += STATEMENT_OFFSET_Y
        frame.height = self.current_position_y - frame.y

        # positioning on frame end
        self.reset_offset_per_gap()
        self.current_position_y += STATEMENT_OFFSET_Y

        # set frame width
        min_x = min(p.lifeline.center_x() for p in frame_info.participants) - CONTROL_FRAME_SPACING
        max_x = max(p.lifeline.center_x() for p in frame_info.participants) + CONTROL_FRAME_SPACING

        if frame_info.inner_frames:
            inner_frame_min_x = min(f.frame.x for f in frame_info.inner_frames) - CONTROL_FRAME_SPACING
            inner_frame_max_x = max(f.frame.x + f.frame.width for f in frame_info.inner_frames) + CONTROL_FRAME_SPACING

            min_x = min(min_x, inner_frame_min_x)
            max_x = max(max_x, inner_frame_max_x)

        frame.x = min_x
        frame.width = max_x - min_x

        # pop frame stack
        self.frame_stack.pop()

    def handle_spacing(self, statement: seqast.SpacingStatement):
        self.current_position_y += statement.spacing

    def reset_offset_per_gap(self):
        self.last_offset_per_gap = {k: self.current_position_y for k in self.last_offset_per_gap}

    def ensure_message_spacing(self, part1: ParticipantInfo, part2: ParticipantInfo, message_dy: int):
        start_gap = min(part1.index, part2.index)
        end_gap = max(part1.index, part2.index)

        max_offset = max(self.last_offset_per_gap[gap] for gap in range(start_gap, end_gap))
        current_spacing = self.current_position_y - max_offset
        required_spacing = MESSAGE_MIN_SPACING - message_dy

        if current_spacing < required_spacing:
            self.current_position_y += required_spacing - current_spacing

            # round up to the next statement offset
            self.current_position_y = ((
                                               self.current_position_y + STATEMENT_OFFSET_Y - 1) // STATEMENT_OFFSET_Y) * STATEMENT_OFFSET_Y

        for gap in range(start_gap, end_gap):
            self.last_offset_per_gap[gap] = self.current_position_y + message_dy

    @staticmethod
    def create_message(sender: ParticipantInfo,
                       receiver: ParticipantInfo,
                       statement: seqast.MessageStatement) -> drawio.Message:
        message = drawio.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line
        message.arrow = statement.arrow
        message.type = drawio.MessageAnchor.NONE
        return message

    def add_frame_participants(self, *args):
        if self.frame_stack:
            self.frame_stack[-1].participants.update(args)

    def activate_participant(self, participant: ParticipantInfo, activator: Optional[ParticipantInfo] = None):
        activation = drawio.Activation(participant.lifeline)
        activation.y = self.current_position_y

        if not participant.activation_stack:
            # if participant is not active we always start in the middle
            activation.dx = 0

        elif len(participant.activation_stack) == 1:
            # if participant is activated once, we consider the location of the activator
            if not activator or activator.index > participant.index:
                next_dx = ACTIVATION_STACK_OFFSET_X
            else:
                next_dx = -ACTIVATION_STACK_OFFSET_X

            activation.dx = next_dx

        else:
            # if participant is activated multiple times, we keep stacking into the same direction
            if participant.activation_stack[-1].dx > participant.activation_stack[-2].dx:
                next_dx = ACTIVATION_STACK_OFFSET_X
            else:
                next_dx = -ACTIVATION_STACK_OFFSET_X

            activation.dx = participant.activation_stack[-1].dx + next_dx

        participant.activation_stack.append(activation)

    def deactivate_participant(self, participant: ParticipantInfo):
        activation = participant.activation_stack.pop()
        activation.height = self.current_position_y - activation.y
