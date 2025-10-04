from dataclasses import dataclass
from typing import List, Dict, Optional

import seqast
import drawio

LIFELINE_WIDTH = 160
LIFELINE_SPACING = 40

TITLE_FRAME_PADDING = 30

START_OFFSET = 60
END_OFFSET = 20

STATEMENT_OFFSET = 10
MESSAGE_MIN_SPACING = 20

ACTIVATION_STACK_OFFSET = drawio.ACTIVATION_WIDTH / 2


@dataclass
class ParticipantInfo:
    index: int
    participant: seqast.ParticipantDeclaration
    lifeline: drawio.Lifeline
    activation_stack: List[drawio.Activation] = None

    def __post_init__(self):
        if not self.activation_stack:
            self.activation_stack = []


class Layouter:
    def __init__(self, description: seqast.SeqDescription):
        self.description = description
        self.participant_info: Dict[str, ParticipantInfo] = {}
        self.last_offset_per_gap: Dict[int, int] = {i: 0 for i in range(len(description.participants) - 1)}
        self.current_offset = START_OFFSET

        self.file = drawio.File()
        self.page = drawio.Page(self.file, 'Diagram')
        self.frame = drawio.Frame(self.page, '')

        self.executed = False

    def layout(self) -> drawio.File:
        assert not self.executed, "layouter instance can only be used once"
        self.executed = True

        self.initialize()
        self.process_statements()
        self.finalize()

        return self.file

    def initialize(self):
        end_x = 0

        for index, participant in enumerate(self.description.participants):
            lifeline = drawio.Lifeline(self.page, participant.name)

            lifeline.width = LIFELINE_WIDTH
            lifeline.x = index * (LIFELINE_WIDTH + LIFELINE_SPACING)

            end_x = lifeline.x + LIFELINE_WIDTH

            self.participant_info[participant.alias] = ParticipantInfo(index, participant, lifeline)

        self.frame.value = self.description.title
        self.frame.x = -TITLE_FRAME_PADDING
        self.frame.y = -TITLE_FRAME_PADDING - self.frame.header_height
        self.frame.width = end_x + (2 * TITLE_FRAME_PADDING)

    def finalize(self):
        self.current_offset += END_OFFSET

        for participant in self.participant_info.values():
            participant.lifeline.height = self.current_offset

        self.frame.height = (self.current_offset - self.frame.y) + TITLE_FRAME_PADDING

    def process_statements(self):
        handlers = {
            seqast.ActivateStatement: self.handle_activate,
            seqast.DeactivateStatement: self.handle_deactivate,
            seqast.MessageStatement: self.handle_message,
            seqast.SelfCallStatement: self.handle_self_call,
            seqast.SpacingStatement: self.handle_spacing,
        }

        for statement in self.description.statements:
            # noinspection PyTypeChecker
            handlers[type(statement)](statement)

    def handle_activate(self, statement: seqast.ActivateStatement):
        participant = self.participant_info[statement.name]

        self.activate_participant(participant)

        self.current_offset += STATEMENT_OFFSET

    def handle_deactivate(self, statement: seqast.DeactivateStatement):
        participant = self.participant_info[statement.name]
        assert participant.activation_stack, "deactivation not possible, participant is inactive"

        self.deactivate_participant(participant)

        self.current_offset += STATEMENT_OFFSET

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

        self.current_offset += STATEMENT_OFFSET

    def handle_message_regular(self, statement: seqast.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"
        assert receiver.activation_stack, "receiver must be active to receive a message"

        self.ensure_message_spacing(sender, receiver, 0)
        message = self.create_message(sender, receiver, statement)

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_offset
        ))

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

    def handle_message_fireforget(self, statement: seqast.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"

        self.activate_participant(receiver, sender)
        self.current_offset += STATEMENT_OFFSET

        self.ensure_message_spacing(sender, receiver, STATEMENT_OFFSET)
        message = self.create_message(sender, receiver, statement)

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_offset
        ))

        self.current_offset += STATEMENT_OFFSET
        self.deactivate_participant(receiver)

    def ensure_message_spacing(self, part1: ParticipantInfo, part2: ParticipantInfo, message_dy: int):
        start_gap = min(part1.index, part2.index)
        end_gap = max(part1.index, part2.index)

        max_offset = max(self.last_offset_per_gap[gap] for gap in range(start_gap, end_gap))
        current_spacing = self.current_offset - max_offset
        required_spacing = MESSAGE_MIN_SPACING - message_dy

        if current_spacing < required_spacing:
            self.current_offset += required_spacing - current_spacing

            # round up to the next statement offset
            self.current_offset = ((self.current_offset + STATEMENT_OFFSET - 1) // STATEMENT_OFFSET) * STATEMENT_OFFSET

        for gap in range(start_gap, end_gap):
            self.last_offset_per_gap[gap] = self.current_offset + message_dy

    @staticmethod
    def create_message(sender: ParticipantInfo,
                       receiver: ParticipantInfo,
                       statement: seqast.MessageStatement) -> drawio.Message:
        message = drawio.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line
        message.arrow = statement.arrow
        message.type = drawio.MessageAnchor.NONE
        return message

    def handle_self_call(self, statement: seqast.SelfCallStatement):
        participant = self.participant_info[statement.name]

        assert participant.activation_stack, "participant must be active for self call"

        # create activation for self call
        self.current_offset += STATEMENT_OFFSET
        self.activate_participant(participant)

        # create self call message
        regular_activation = participant.activation_stack[-2]
        self_call_activation = participant.activation_stack[-1]
        message = drawio.Message(regular_activation, self_call_activation, statement.text)
        message.alignment = drawio.TextAlignment.MIDDLE_RIGHT

        self_call_x = participant.lifeline.center_x() + self_call_activation.dx + 25

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_offset - STATEMENT_OFFSET,
        ))

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_offset + STATEMENT_OFFSET,
        ))

        # deactivate after self call
        self.current_offset += 2 * STATEMENT_OFFSET
        self.deactivate_participant(participant)

        self.current_offset += STATEMENT_OFFSET

    def activate_participant(self, participant: ParticipantInfo, activator: Optional[ParticipantInfo] = None):
        activation = drawio.Activation(participant.lifeline)
        activation.y = self.current_offset

        if not participant.activation_stack:
            # if participant is not active we always start in the middle
            activation.dx = 0

        elif len(participant.activation_stack) == 1:
            # if participant is activated once, we consider the location of the activator
            if not activator or activator.index > participant.index:
                next_dx = ACTIVATION_STACK_OFFSET
            else:
                next_dx = -ACTIVATION_STACK_OFFSET

            activation.dx = next_dx

        else:
            # if participant is activated multiple times, we keep stacking into the same direction
            if participant.activation_stack[-1].dx > participant.activation_stack[-2].dx:
                next_dx = ACTIVATION_STACK_OFFSET
            else:
                next_dx = -ACTIVATION_STACK_OFFSET

            activation.dx = participant.activation_stack[-1].dx + next_dx

        participant.activation_stack.append(activation)

    def deactivate_participant(self, participant: ParticipantInfo):
        activation = participant.activation_stack.pop()
        activation.height = self.current_offset - activation.y

    def handle_spacing(self, statement: seqast.SpacingStatement):
        self.current_offset += statement.spacing
