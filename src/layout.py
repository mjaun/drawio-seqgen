from typing import List, Optional, Iterable

import seqast
import drawio

PARTICIPANT_DEFAULT_BOX_WIDTH = 160
PARTICIPANT_DEFAULT_SPACING = 40
PARTICIPANT_BOX_HEIGHT = 40

TITLE_FRAME_DEFAULT_BOX_WIDTH = 160
TITLE_FRAME_DEFAULT_BOX_HEIGHT = 30
TITLE_FRAME_PADDING = 30

CONTROL_FRAME_BOX_WIDTH = 60
CONTROL_FRAME_BOX_HEIGHT = 20
CONTROL_FRAME_PADDING = 30

NOTE_DEFAULT_WIDTH = 100
NOTE_DEFAULT_HEIGHT = 40

SELF_CALL_MIN_TEXT_WIDTH = 30
SELF_CALL_MESSAGE_DX = 25
SELF_CALL_MESSAGE_ACTIVATION_SPACING = 10
SELF_CALL_ACTIVATION_HEIGHT = 20

FIREFORGET_ACTIVATION_HEIGHT = 20

STATEMENT_OFFSET_Y = 10
MESSAGE_MIN_SPACING = 20

ACTIVATION_STACK_OFFSET_X = drawio.ACTIVATION_WIDTH / 2
MESSAGE_ANCHOR_DY = drawio.MESSAGE_ANCHOR_DY


class PositionIndicator:
    def __init__(self):
        self.y = 0


class ParticipantInfo:
    def __init__(self, index: int, name: str, lifeline: drawio.Lifeline):
        self.index = index
        self.name = name
        self.lifeline = lifeline
        self.activation_stack: List[drawio.Activation] = []
        self.center_indicator: PositionIndicator = PositionIndicator()
        self.left_indicator: PositionIndicator = PositionIndicator()
        self.right_indicator: PositionIndicator = PositionIndicator()


class FrameDimension:
    def __init__(self):
        self.min_x: Optional[float] = None
        self.max_x: Optional[float] = None


class Layouter:
    def __init__(self, page: drawio.Page):
        self.page = page

        self.participants: List[ParticipantInfo] = []
        self.frame_dimension_stack: List[FrameDimension] = []

        self.current_position_y = PARTICIPANT_BOX_HEIGHT + (2 * STATEMENT_OFFSET_Y)
        self.participant_width = PARTICIPANT_DEFAULT_BOX_WIDTH
        self.participant_spacing = PARTICIPANT_DEFAULT_SPACING

        self.title_frame: Optional[drawio.Frame] = None

        self.frame_dimension_stack.append(FrameDimension())
        self.update_frame_dimension(0)

        self.executed = False

    def layout(self, statements: List[seqast.Statement]):
        assert not self.executed, "layouter instance can only be used once"
        self.executed = True

        self.process_statements(statements)

        self.finalize_participants()
        self.finalize_title_frame()

    def finalize_participants(self):
        self.vertical_offset((2 * STATEMENT_OFFSET_Y))

        for participant in self.participants:
            assert not participant.activation_stack, f"participants must be inactive at end: {participant.name}"
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
            seqast.TitleWidthStatement: self.handle_title_width,
            seqast.TitleHeightStatement: self.handle_title_height,
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
                # noinspection PyTypeChecker, PyArgumentList
                handlers[type(statement)](statement)
            except:
                raise RuntimeError(f'error processing statement on line {statement.line_number}')

    def handle_title(self, statement: seqast.TitleStatement):
        assert not self.title_frame, "title may occur only once"
        self.title_frame = drawio.Frame(self.page, statement.text)
        self.title_frame.box_width = TITLE_FRAME_DEFAULT_BOX_WIDTH
        self.title_frame.box_height = TITLE_FRAME_DEFAULT_BOX_HEIGHT

    def handle_title_width(self, statement: seqast.TitleWidthStatement):
        self.title_frame.box_width = statement.width

    def handle_title_height(self, statement: seqast.TitleHeightStatement):
        self.title_frame.box_height = statement.height

    def handle_participant(self, statement: seqast.ParticipantStatement):
        assert not self.participant_by_name(statement.name), "participant already exists"

        first_participant = len(self.participants) == 0
        index = len(self.participants)

        lifeline = drawio.Lifeline(self.page, statement.text)
        lifeline.width = self.participant_width
        lifeline.box_height = PARTICIPANT_BOX_HEIGHT

        if not first_participant:
            prev_lifeline = self.participants[-1].lifeline
            lifeline.x = prev_lifeline.x + prev_lifeline.width + self.participant_spacing

        participant = ParticipantInfo(index, statement.name, lifeline)

        if not first_participant:
            participant.left_indicator = self.participants[-1].right_indicator

        self.participants.append(participant)
        self.update_frame_dimension(lifeline.x + lifeline.width)

    def handle_participant_width(self, statement: seqast.ParticipantWidthStatement):
        self.participant_width = statement.width

    def handle_participant_spacing(self, statement: seqast.ParticipantSpacingStatement):
        self.participant_spacing = statement.spacing

    def handle_activate(self, statement: seqast.ActivateStatement):
        for name in statement.targets:
            participant = self.participant_by_name(name)
            self.activate_participant(participant)
            self.update_frame_dimension(participant.lifeline.center_x())

        self.vertical_offset(STATEMENT_OFFSET_Y)

    def handle_deactivate(self, statement: seqast.DeactivateStatement):
        for name in statement.targets:
            participant = self.participant_by_name(name)
            assert participant.activation_stack, "deactivation not possible, participant is inactive"
            self.deactivate_participant(participant)
            self.update_position_indicator(participant.center_indicator)
            self.update_frame_dimension(participant.lifeline.center_x())

        self.vertical_offset(STATEMENT_OFFSET_Y)

    def handle_message(self, statement: seqast.MessageStatement):
        handlers = {
            seqast.MessageActivationType.REGULAR: self.handle_message_regular,
            seqast.MessageActivationType.ACTIVATE: self.handle_message_activate,
            seqast.MessageActivationType.DEACTIVATE: self.handle_message_deactivate,
            seqast.MessageActivationType.FIREFORGET: self.handle_message_fireforget,
        }

        # noinspection PyArgumentList
        handlers[statement.activation](statement)

    def handle_message_regular(self, statement: seqast.MessageStatement):
        sender = self.participant_by_name(statement.sender)
        receiver = self.participant_by_name(statement.receiver)

        assert sender.activation_stack, "sender must be active to send a message"
        assert statement.sender != statement.receiver, "use self call syntax"
        assert receiver.activation_stack, "receiver must be active to receive a message"

        self.ensure_vertical_spacing_between(sender, receiver, MESSAGE_MIN_SPACING)

        message = drawio.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line_style
        message.arrow = statement.arrow_style

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_position_y
        ))

        self.update_position_indicators_between(sender, receiver)

        self.vertical_offset(STATEMENT_OFFSET_Y)
        self.update_frame_dimension(sender.lifeline.center_x(), receiver.lifeline.center_x())

    def handle_message_activate(self, statement: seqast.MessageStatement):
        sender = self.participant_by_name(statement.sender)
        receiver = self.participant_by_name(statement.receiver)

        assert sender.activation_stack, "sender must be active to send a message"
        assert statement.sender != statement.receiver, "use self call syntax"

        self.ensure_vertical_spacing_between(sender, receiver, MESSAGE_MIN_SPACING - MESSAGE_ANCHOR_DY)
        self.activate_participant(receiver, sender)
        self.vertical_offset(MESSAGE_ANCHOR_DY)

        message = drawio.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line_style
        message.arrow = statement.arrow_style

        if sender.index < receiver.index:
            message.type = drawio.MessageAnchor.TOP_LEFT
        else:
            message.type = drawio.MessageAnchor.TOP_RIGHT

        self.update_position_indicators_between(sender, receiver)

        self.vertical_offset(STATEMENT_OFFSET_Y)
        self.update_frame_dimension(sender.lifeline.center_x(), receiver.lifeline.center_x())

    def handle_message_deactivate(self, statement: seqast.MessageStatement):
        sender = self.participant_by_name(statement.sender)
        receiver = self.participant_by_name(statement.receiver)

        assert sender.activation_stack, "sender must be active to send a message"
        assert statement.sender != statement.receiver, "use self call syntax"
        assert receiver.activation_stack, "receiver must be active to receive a message"

        self.ensure_vertical_spacing_between(sender, receiver, MESSAGE_MIN_SPACING)

        message = drawio.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line_style
        message.arrow = statement.arrow_style

        if sender.index < receiver.index:
            message.type = drawio.MessageAnchor.BOTTOM_RIGHT
        else:
            message.type = drawio.MessageAnchor.BOTTOM_LEFT

        self.update_position_indicators_between(sender, receiver)
        self.vertical_offset(MESSAGE_ANCHOR_DY)
        self.deactivate_participant(sender)
        self.update_position_indicator(sender.center_indicator)

        self.vertical_offset(STATEMENT_OFFSET_Y)
        self.update_frame_dimension(sender.lifeline.center_x(), receiver.lifeline.center_x())


    def handle_message_fireforget(self, statement: seqast.MessageStatement):
        sender = self.participant_by_name(statement.sender)
        receiver = self.participant_by_name(statement.receiver)

        assert sender.activation_stack, "sender must be active to send a message"
        assert statement.sender != statement.receiver, "use self call syntax"

        self.ensure_vertical_spacing_between(sender, receiver, MESSAGE_MIN_SPACING - (FIREFORGET_ACTIVATION_HEIGHT / 2))
        self.activate_participant(receiver, sender)
        self.vertical_offset(FIREFORGET_ACTIVATION_HEIGHT / 2)

        message = drawio.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line_style
        message.arrow = statement.arrow_style

        message.points.append(drawio.Point(
            x=(sender.lifeline.center_x() + receiver.lifeline.center_x()) / 2,
            y=self.current_position_y
        ))

        self.update_position_indicators_between(sender, receiver)
        self.vertical_offset(FIREFORGET_ACTIVATION_HEIGHT / 2)
        self.deactivate_participant(receiver)
        self.update_position_indicator(sender.center_indicator)

        self.vertical_offset(STATEMENT_OFFSET_Y)
        self.update_frame_dimension(sender.lifeline.center_x(), receiver.lifeline.center_x())

    def handle_self_call(self, statement: seqast.SelfCallStatement):
        participant = self.participant_by_name(statement.target)

        assert participant.activation_stack, "participant must be active for self call"

        # create activation for self call
        self.vertical_offset(SELF_CALL_MESSAGE_ACTIVATION_SPACING)
        self.activate_participant(participant)

        regular_activation = participant.activation_stack[-2]
        self_call_activation = participant.activation_stack[-1]

        # create self call message
        message = drawio.Message(regular_activation, self_call_activation, statement.text)
        message.alignment = drawio.TextAlignment.MIDDLE_LEFT

        lifeline_x = participant.lifeline.center_x()
        self_call_x = lifeline_x + self_call_activation.dx + SELF_CALL_MESSAGE_DX

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_position_y - SELF_CALL_MESSAGE_ACTIVATION_SPACING,
        ))

        message.points.append(drawio.Point(
            x=self_call_x,
            y=self.current_position_y + (SELF_CALL_ACTIVATION_HEIGHT / 2),
        ))

        # deactivate after self call
        self.vertical_offset(SELF_CALL_ACTIVATION_HEIGHT)
        self.deactivate_participant(participant)

        self.update_frame_dimension(lifeline_x, self_call_x + SELF_CALL_MIN_TEXT_WIDTH)
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
            self.update_all_position_indicators()
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
        participant = self.participant_by_name(statement.target)

        note = drawio.Note(self.page, statement.text)
        note.x = participant.lifeline.center_x() + (statement.dx or 0)
        note.y = self.current_position_y + (statement.dy or 0)
        note.width = statement.width or NOTE_DEFAULT_WIDTH
        note.height = statement.height or NOTE_DEFAULT_HEIGHT

    def handle_vertical_offset(self, statement: seqast.VerticalOffsetStatement):
        self.vertical_offset(statement.spacing)

        for indicator in self.all_position_indicators():
            indicator.y += statement.spacing

    def handle_frame_dimension(self, statement: seqast.FrameDimensionStatement):
        participant = self.participant_by_name(statement.target)
        lifeline_x = participant.lifeline.center_x()
        self.update_frame_dimension(lifeline_x + statement.dx)

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
        self.update_all_position_indicators()
        self.vertical_offset(STATEMENT_OFFSET_Y)

        return frame

    def close_frame(self, frame: drawio.Frame):
        # set frame height
        self.vertical_offset(STATEMENT_OFFSET_Y)
        frame.height = self.current_position_y - frame.y

        # positioning on frame end
        self.update_all_position_indicators()
        self.vertical_offset(STATEMENT_OFFSET_Y)

        # pop frame stack
        dimension = self.frame_dimension_stack.pop()

        # set frame width
        assert dimension.min_x is not None and dimension.max_x is not None, "unknown frame dimension"
        frame.x = dimension.min_x - CONTROL_FRAME_PADDING
        frame.width = dimension.max_x + CONTROL_FRAME_PADDING - frame.x

        # update dimension for parent frame
        self.update_frame_dimension(frame.x, frame.x + frame.width)

    def update_frame_dimension(self, *x: float):
        dimension = self.frame_dimension_stack[-1]

        if dimension.min_x is None:
            dimension.min_x = min(x)
        else:
            dimension.min_x = min(dimension.min_x, min(x))

        if dimension.max_x is None:
            dimension.max_x = max(x)
        else:
            dimension.max_x = max(dimension.max_x, max(x))

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

    def participant_by_name(self, name: str) -> ParticipantInfo:
        return next((p for p in self.participants if p.name == name), None)

    def ensure_vertical_spacing_between(self, first: ParticipantInfo, second: ParticipantInfo, required_spacing: float):
        for indicator in self.position_indicators_between(first, second):
            self.ensure_vertical_spacing(indicator, required_spacing)

    def ensure_vertical_spacing(self, indicator: PositionIndicator, required_spacing: float):
        current_spacing = (self.current_position_y - indicator.y)

        if current_spacing < required_spacing:
            self.vertical_offset(required_spacing - current_spacing)

    def update_position_indicators_between(self, first: ParticipantInfo, second: ParticipantInfo):
        for indicator in self.position_indicators_between(first, second):
            self.update_position_indicator(indicator)

    def update_all_position_indicators(self):
        for indicator in self.all_position_indicators():
            self.update_position_indicator(indicator)

    def update_position_indicator(self, indicator: PositionIndicator):
        indicator.y = self.current_position_y

    def position_indicators_between(self, first: ParticipantInfo, second: ParticipantInfo) \
            -> Iterable[PositionIndicator]:
        start_index = min(first.index, second.index)
        end_index = max(first.index, second.index)

        for participant in self.participants[start_index:end_index]:
            yield participant.center_indicator

            if participant.index != end_index:
                yield participant.right_indicator

    def all_position_indicators(self) -> Iterable[PositionIndicator]:
        if self.participants:
            yield self.participants[0].left_indicator

        for participant in self.participants:
            yield participant.center_indicator
            yield participant.right_indicator

    def vertical_offset(self, dy: float):
        self.current_position_y += dy
