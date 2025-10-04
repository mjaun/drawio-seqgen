from dataclasses import dataclass
from typing import List, Dict, Optional

import model
import output

LIFELINE_WIDTH = 120
LIFELINE_SPACING = 40

TITLE_FRAME_PADDING = 30

START_OFFSET = 60
END_OFFSET = 20

STATEMENT_OFFSET = 10
MESSAGE_MIN_SPACING = 20


@dataclass
class ParticipantInfo:
    index: int
    participant: model.ParticipantDeclaration
    lifeline: output.Lifeline
    activation_stack: List[output.Activation] = None

    def __post_init__(self):
        if not self.activation_stack:
            self.activation_stack = []


class Layouter:
    def __init__(self, description: model.SequenceDiagramDescription):
        self.description = description
        self.participant_info: Dict[str, ParticipantInfo] = {}
        self.last_offset_per_gap: Dict[int, int] = {i: 0 for i in range(len(description.participants) - 1)}
        self.current_offset = START_OFFSET

        self.file = output.File()
        self.page = output.Page(self.file, 'Diagram')
        self.frame = output.Frame(self.page, '')

        self.executed = False

    def layout(self) -> output.File:
        assert not self.executed, "layouter instance can only be used once"
        self.executed = True

        self.initialize()
        self.process_statements()
        self.finalize()

        return self.file

    def initialize(self):
        end_x = 0

        for index, participant in enumerate(self.description.participants):
            lifeline = output.Lifeline(self.page, participant.name)

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
            model.ActivateStatement: self.handle_activate,
            model.DeactivateStatement: self.handle_deactivate,
            model.MessageStatement: self.handle_message,
            model.SpacingStatement: self.handle_spacing,
        }

        for statement in self.description.statements:
            # noinspection PyTypeChecker
            handlers[type(statement)](statement)

    def handle_activate(self, statement: model.ActivateStatement):
        info = self.participant_info[statement.name]
        assert not info.activation_stack, "explicit activation allowed only if object is inactive"

        self.activate_participant(info)

        self.current_offset += STATEMENT_OFFSET

    def handle_deactivate(self, statement: model.DeactivateStatement):
        info = self.participant_info[statement.name]
        assert info.activation_stack, "explicit deactivation not possible, participant is inactive"

        self.deactivate_participant(info)

        self.current_offset += STATEMENT_OFFSET

    def handle_message(self, statement: model.MessageStatement):
        assert statement.sender != statement.receiver, "use self call syntax"

        handlers = {
            model.MessageActivationType.REGULAR: self.handle_message_regular,
            model.MessageActivationType.ACTIVATE: self.handle_message_activate,
            model.MessageActivationType.DEACTIVATE: self.handle_message_deactivate,
            model.MessageActivationType.FIREFORGET: self.handle_message_fireforget,
        }

        # noinspection PyArgumentList
        handlers[statement.activation](statement)

        self.current_offset += STATEMENT_OFFSET

    def handle_message_regular(self, statement: model.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"
        assert receiver.activation_stack, "receiver must be active to receive a message"

        self.ensure_message_spacing(sender, receiver, 0)

        message = self.create_message(sender, receiver, statement)
        message.type = output.MessageType.REGULAR
        message.y = self.current_offset

    def handle_message_activate(self, statement: model.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"

        self.ensure_message_spacing(sender, receiver, output.ACTIVATION_MESSAGE_DY)
        self.activate_participant(receiver, sender)

        if sender.index < receiver.index:
            message_type = output.MessageType.ACTIVATE_LEFT
        else:
            message_type = output.MessageType.ACTIVATE_RIGHT

        message = self.create_message(sender, receiver, statement)
        message.type = message_type

    def handle_message_deactivate(self, statement: model.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"
        assert receiver.activation_stack, "receiver must be active to receive a message"

        self.ensure_message_spacing(sender, receiver, -output.ACTIVATION_MESSAGE_DY)

        if sender.index < receiver.index:
            message_type = output.MessageType.DEACTIVATE_RIGHT
        else:
            message_type = output.MessageType.DEACTIVATE_LEFT

        message = self.create_message(sender, receiver, statement)
        message.type = message_type

        self.deactivate_participant(sender)

    def handle_message_fireforget(self, statement: model.MessageStatement):
        sender = self.participant_info[statement.sender]
        receiver = self.participant_info[statement.receiver]

        assert sender.activation_stack, "sender must be active to send a message"

        self.activate_participant(receiver, sender)

        self.current_offset += STATEMENT_OFFSET

        self.ensure_message_spacing(sender, receiver, STATEMENT_OFFSET)

        message = self.create_message(sender, receiver, statement)
        message.type = output.MessageType.REGULAR
        message.y = self.current_offset

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
                       statement: model.MessageStatement) -> output.Message:
        message = output.Message(sender.activation_stack[-1], receiver.activation_stack[-1], statement.text)
        message.line = statement.line
        message.arrow = statement.arrow
        return message

    def activate_participant(self, participant: ParticipantInfo, activator: Optional[ParticipantInfo] = None):
        activation = output.Activation(participant.lifeline)
        activation.y = self.current_offset

        if activator and participant.activation_stack:
            last_dx = participant.activation_stack[-1].dx

            if activator.index > participant.index:
                current_dx = output.ACTIVATION_WIDTH / 2
            else:
                current_dx = -output.ACTIVATION_WIDTH / 2

            activation.dx = last_dx + current_dx

        participant.activation_stack.append(activation)

    def deactivate_participant(self, participant: ParticipantInfo):
        activation = participant.activation_stack.pop()
        activation.height = self.current_offset - activation.y

    def handle_spacing(self, statement: model.SpacingStatement):
        self.current_offset += statement.spacing
