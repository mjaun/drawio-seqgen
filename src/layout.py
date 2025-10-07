from typing import List, Dict, Optional

import seqast
import drawio

PARTICIPANT_DEFAULT_BOX_WIDTH = 160
PARTICIPANT_DEFAULT_SPACING = 40
PARTICIPANT_BOX_HEIGHT = 40

TITLE_FRAME_DEFAULT_BOX_WIDTH = 160
TITLE_FRAME_DEFAULT_BOX_HEIGHT = 40
TITLE_FRAME_PADDING = 30

CONTROL_FRAME_BOX_WIDTH = 60
CONTROL_FRAME_BOX_HEIGHT = 20
CONTROL_FRAME_PADDING = 30

NOTE_DEFAULT_WIDTH = 100
NOTE_DEFAULT_HEIGHT = 40

SELF_CALL_WIDTH = 30

STATEMENT_OFFSET_Y = 10
MESSAGE_MIN_SPACING = 20

ACTIVATION_STACK_OFFSET_X = drawio.ACTIVATION_WIDTH / 2


class ParticipantInfo:
    def __init__(self, index: int, lifeline: drawio.Lifeline):
        self.index = index
        self.lifeline = lifeline
        self.activation_stack: List[drawio.Activation] = []
        self.last_position_y = 0  # refers to messages between this participant and the participant to the right


class FrameDimension:
    def __init__(self):
        self.min_x: Optional[int] = None
        self.max_x: Optional[int] = None


class Layouter:
    def __init__(self, page: drawio.Page):
        self.page = page

        self.participant_dict: Dict[str, ParticipantInfo] = {}
        self.frame_dimension_stack: List[FrameDimension] = []

        self.current_position_y = PARTICIPANT_BOX_HEIGHT + (2 * STATEMENT_OFFSET_Y)
        self.participant_width = PARTICIPANT_DEFAULT_BOX_WIDTH
        self.participant_spacing = PARTICIPANT_DEFAULT_SPACING
        self.participant_end_x = 0

        self.title_frame: Optional[drawio.Frame] = None

        self.frame_dimension_stack.append(FrameDimension())
        self.request_frame_dimension(0)

        self.executed = False

    def layout(self, statements: List[seqast.Statement]):
        assert not self.executed, "layouter instance can only be used once"
        self.executed = True

        self.process_statements(statements)

        self.finalize_participants()
        self.finalize_title_frame()

    def finalize_participants(self):
        self.vertical_offset((2 * STATEMENT_OFFSET_Y))

        for name, participant in self.participant_dict.items():
            assert not participant.activation_stack, f"participants must be inactive at end: {name}"
            participant.lifeline.height = self.current_position_y

    def finalize_title_frame(self):
        assert len(self.frame_dimension_stack) == 1
        dimensions = self.frame_dimension_stack.pop()

        if not self.title_frame:
            return

        self.title_frame.x = dimensions.min_x - TITLE_FRAME_PADDING
        self.title_frame.y = -TITLE_FRAME_PADDING - self.title_frame.box_height
        self.title_frame.width = dimensions.max_x + TITLE_FRAME_PADDING - self.title_frame.x
        self.title_frame.height = (self.current_position_y - self.title_frame.y) + TITLE_FRAME_PADDING

    def process_statements(self, statements: List[seqast.Statement]):
        handlers = {
            seqast.TitleStatement: self.handle_title,
            seqast.TitleSizeStatement: self.handle_title_size,
            seqast.ParticipantStatement: self.handle_participant,
            seqast.ParticipantWidthStatement: self.handle_participant_width,
            seqast.ParticipantSpacingStatement: self.handle_participant_spacing,
            seqast.ActivateStatement: self.handle_activate,
            seqast.DeactivateStatement: self.handle_deactivate,
            seqast.MessageStatement: self.handle_message,
            seqast.SelfCallStatement: self.handle_self_call,
            seqast.AlternativeStatement: self.handle_alternative,
            seqast.OptionStatement: self.handle_option,
            seqast.LoopStatement: self.handle_loop,
            seqast.NoteStatement: self.handle_note,
            seqast.VerticalOffsetStatement: self.handle_vertical_offset,
            seqast.FrameDimensionStatement: self.handle_frame_dimension,
        }

        for statement in statements:
            try:
                # noinspection PyTypeChecker
                handlers[type(statement)](statement)
            except:
                raise RuntimeError(f'error processing statement on line {statement.line_number}')

    def handle_title(self, statement: seqast.TitleStatement):
        assert not self.title_frame, "title may occur only once"
        self.title_frame = drawio.Frame(self.page, statement.text)
        self.title_frame.box_width = TITLE_FRAME_DEFAULT_BOX_WIDTH
        self.title_frame.box_height = TITLE_FRAME_DEFAULT_BOX_HEIGHT

    def handle_title_size(self, statement: seqast.TitleSizeStatement):
        self.title_frame.box_width = statement.width
        self.title_frame.box_height = statement.height

    def handle_participant(self, statement: seqast.ParticipantStatement):
        first_participant = len(self.participant_dict) == 0
        index = len(self.participant_dict)

        lifeline = drawio.Lifeline(self.page, statement.text)
        lifeline.x = self.participant_end_x + self.participant_spacing if not first_participant else 0
        lifeline.width = self.participant_width
        lifeline.height = PARTICIPANT_BOX_HEIGHT

        assert statement.name not in self.participant_dict, "participant already exists"
        self.participant_dict[statement.name] = ParticipantInfo(index, lifeline)
        self.participant_end_x = lifeline.x + lifeline.width
        self.request_frame_dimension(self.participant_end_x)

    def handle_participant_width(self, statement: seqast.ParticipantWidthStatement):
        self.participant_width = statement.width

    def handle_participant_spacing(self, statement: seqast.ParticipantSpacingStatement):
        self.participant_spacing = statement.spacing

    def handle_activate(self, statement: seqast.ActivateStatement):
        participant = self.participant_dict[statement.target]

        self.activate_participant(participant)
        self.request_frame_dimension(participant.lifeline.center_x())
        self.vertical_offset(STATEMENT_OFFSET_Y)

    def handle_deactivate(self, statement: seqast.DeactivateStatement):
        participant = self.participant_dict[statement.target]
        assert participant.activation_stack, "deactivation not possible, participant is inactive"

        self.deactivate_participant(participant)
        self.request_frame_dimension(participant.lifeline.center_x())
        self.vertical_offset(STATEMENT_OFFSET_Y)

    def handle_message(self, statement: seqast.MessageStatement):
        sender = self.participant_dict[statement.sender]
        receiver = self.participant_dict[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"
        assert statement.sender != statement.receiver, "use self call syntax"

        handlers = {
            seqast.MessageActivationType.REGULAR: self.handle_message_regular,
            seqast.MessageActivationType.ACTIVATE: self.handle_message_activate,
            seqast.MessageActivationType.DEACTIVATE: self.handle_message_deactivate,
            seqast.MessageActivationType.FIREFORGET: self.handle_message_fireforget,
        }

        # noinspection PyArgumentList
        handlers[statement.activation](statement)

        self.request_frame_dimension(sender.lifeline.center_x(), receiver.lifeline.center_x())
        self.vertical_offset(STATEMENT_OFFSET_Y)

    def handle_message_regular(self, statement: seqast.MessageStatement):
        sender = self.participant_dict[statement.sender]
        receiver = self.participant_dict[statement.receiver]

        assert receiver.activation_stack, "receiver must be active to receive a message"

        self.ensure_message_spacing(sender, receiver, 0)
        message = self.create_message(sender, receiver, statement)

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_position_y
        ))

    def handle_message_activate(self, statement: seqast.MessageStatement):
        sender = self.participant_dict[statement.sender]
        receiver = self.participant_dict[statement.receiver]

        self.ensure_message_spacing(sender, receiver, drawio.MESSAGE_ANCHOR_DY)
        self.activate_participant(receiver, sender)
        message = self.create_message(sender, receiver, statement)

        if sender.index < receiver.index:
            message.type = drawio.MessageAnchor.TOP_LEFT
        else:
            message.type = drawio.MessageAnchor.TOP_RIGHT

    def handle_message_deactivate(self, statement: seqast.MessageStatement):
        sender = self.participant_dict[statement.sender]
        receiver = self.participant_dict[statement.receiver]

        assert receiver.activation_stack, "deactivation not possible, participant is inactive"

        self.ensure_message_spacing(sender, receiver, -drawio.MESSAGE_ANCHOR_DY)
        message = self.create_message(sender, receiver, statement)

        if sender.index < receiver.index:
            message.type = drawio.MessageAnchor.BOTTOM_RIGHT
        else:
            message.type = drawio.MessageAnchor.BOTTOM_LEFT

        self.deactivate_participant(sender)

    def handle_message_fireforget(self, statement: seqast.MessageStatement):
        sender = self.participant_dict[statement.sender]
        receiver = self.participant_dict[statement.receiver]

        self.activate_participant(receiver, sender)
        self.vertical_offset(STATEMENT_OFFSET_Y)

        self.ensure_message_spacing(sender, receiver, STATEMENT_OFFSET_Y)
        message = self.create_message(sender, receiver, statement)

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_position_y
        ))

        self.vertical_offset(STATEMENT_OFFSET_Y)
        self.deactivate_participant(receiver)

    def handle_self_call(self, statement: seqast.SelfCallStatement):
        participant = self.participant_dict[statement.target]

        assert participant.activation_stack, "participant must be active for self call"

        # create activation for self call
        self.vertical_offset(STATEMENT_OFFSET_Y)
        self.activate_participant(participant)

        # create self call message
        regular_activation = participant.activation_stack[-2]
        self_call_activation = participant.activation_stack[-1]
        message = drawio.Message(regular_activation, self_call_activation, statement.text)
        message.alignment = drawio.TextAlignment.MIDDLE_RIGHT

        lifeline_x = participant.lifeline.center_x()
        self_call_x = lifeline_x + self_call_activation.dx + 25

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_position_y - STATEMENT_OFFSET_Y,
        ))

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_position_y + STATEMENT_OFFSET_Y,
        ))

        # deactivate after self call
        self.vertical_offset(2 * STATEMENT_OFFSET_Y)
        self.deactivate_participant(participant)

        self.request_frame_dimension(lifeline_x, lifeline_x + SELF_CALL_WIDTH)

        self.vertical_offset(STATEMENT_OFFSET_Y)

    def handle_alternative(self, statement: seqast.AlternativeStatement):
        frame = self.open_frame('alt', statement.text)
        self.process_statements(statement.inner)

        for branch in statement.branches:
            self.vertical_offset(STATEMENT_OFFSET_Y)

            separator = drawio.Separator(frame)
            separator.y = self.current_position_y - frame.y

            text = drawio.Text(self.page, frame, f'[{branch.text}]')
            text.x = 10
            text.y = separator.y + 5

            self.vertical_offset(30)
            self.reset_vertical_position_per_gap()
            self.vertical_offset(STATEMENT_OFFSET_Y)

            self.process_statements(branch.inner)

        self.close_frame(frame)

    def handle_option(self, statement: seqast.OptionStatement):
        frame = self.open_frame('opt', statement.text)
        self.process_statements(statement.inner)
        self.close_frame(frame)

    def handle_loop(self, statement: seqast.LoopStatement):
        frame = self.open_frame('loop', statement.text)
        self.process_statements(statement.inner)
        self.close_frame(frame)

    def handle_note(self, statement: seqast.NoteStatement):
        participant = self.participant_dict[statement.target]

        note = drawio.Note(self.page, statement.text)
        note.x = participant.lifeline.center_x() + (statement.dx or 0)
        note.y = self.current_position_y + (statement.dy or 0)
        note.width = statement.width or NOTE_DEFAULT_WIDTH
        note.height = statement.height or NOTE_DEFAULT_HEIGHT

    def handle_vertical_offset(self, statement: seqast.VerticalOffsetStatement):
        self.vertical_offset(statement.spacing)

    def handle_frame_dimension(self, statement: seqast.FrameDimensionStatement):
        participant = self.participant_dict[statement.target]
        lifeline_x = participant.lifeline.center_x()
        self.request_frame_dimension(lifeline_x + statement.dx)

    @staticmethod
    def create_message(sender: ParticipantInfo,
                       receiver: ParticipantInfo,
                       statement: seqast.MessageStatement) -> drawio.Message:
        message = drawio.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line_style
        message.arrow = statement.arrow_style
        message.type = drawio.MessageAnchor.NONE
        return message

    def vertical_offset(self, dy: int):
        self.current_position_y += dy

    def reset_vertical_position_per_gap(self):
        for participant in self.participant_dict.values():
            participant.last_position_y = self.current_position_y

    def ensure_message_spacing(self, part1: ParticipantInfo, part2: ParticipantInfo, message_dy: int):
        # determine the max vertical position occupied in the gaps between the two participants
        start_index = min(part1.index, part2.index)
        end_index = max(part1.index, part2.index)
        participants = [p for p in self.participant_dict.values() if p.index in range(start_index, end_index)]
        max_position_y = max(p.last_position_y for p in participants)

        # add vertical offset if needed
        current_spacing = self.current_position_y - max_position_y
        required_spacing = MESSAGE_MIN_SPACING - message_dy

        if current_spacing < required_spacing:
            dy = round_up_int(required_spacing - current_spacing, STATEMENT_OFFSET_Y)
            self.vertical_offset(dy)

        # update the vertical position occupied by the current message
        for participant in participants:
            participant.last_position_y = self.current_position_y + message_dy

    def request_frame_dimension(self, *x: int):
        dimension = self.frame_dimension_stack[-1]

        if dimension.min_x is None:
            dimension.min_x = min(x)
        else:
            dimension.min_x = min(dimension.min_x, min(x))

        if dimension.max_x is None:
            dimension.max_x = max(x)
        else:
            dimension.max_x = max(dimension.max_x, max(x))

    def open_frame(self, value: str, text: str) -> drawio.Frame:
        # create frame
        self.vertical_offset(STATEMENT_OFFSET_Y)

        frame = drawio.Frame(self.page, value)
        frame.y = self.current_position_y
        frame.box_width = CONTROL_FRAME_BOX_WIDTH
        frame.box_height = CONTROL_FRAME_BOX_HEIGHT

        text = drawio.Text(self.page, frame, f'[{text}]')
        text.x = 10
        text.y = CONTROL_FRAME_BOX_HEIGHT + 5

        # push frame stack
        dimension = FrameDimension()
        self.frame_dimension_stack.append(dimension)

        # positioning on frame begin
        self.vertical_offset(CONTROL_FRAME_BOX_HEIGHT + 30)
        self.reset_vertical_position_per_gap()
        self.vertical_offset(STATEMENT_OFFSET_Y)

        return frame

    def close_frame(self, frame: drawio.Frame):
        # set frame height
        self.vertical_offset(STATEMENT_OFFSET_Y)
        frame.height = self.current_position_y - frame.y

        # positioning on frame end
        self.reset_vertical_position_per_gap()
        self.vertical_offset(STATEMENT_OFFSET_Y)

        # pop frame stack
        dimension = self.frame_dimension_stack.pop()

        # set frame width
        assert dimension.min_x is not None and dimension.max_x is not None, "unknown frame dimension"
        frame.x = dimension.min_x - CONTROL_FRAME_PADDING
        frame.width = dimension.max_x + CONTROL_FRAME_PADDING - frame.x

        # request dimension for parent frame
        self.request_frame_dimension(frame.x, frame.x + frame.width)

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


def round_up_int(number: int, multiple: int = 1):
    assert multiple >= 1
    return ((number + multiple - 1) // multiple) * multiple
