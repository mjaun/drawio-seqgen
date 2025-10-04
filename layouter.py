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
            model.ActivateStatement: self.handle_activation,
            model.DeactivateStatement: self.handle_deactivation,
            model.MessageStatement: self.handle_message,
        }

        for statement in self.description.statements:
            if type(statement) not in handlers:
                raise NotImplementedError()

            # noinspection PyTypeChecker
            handlers[type(statement)](statement)

    def handle_activation(self, statement: model.ActivateStatement):
        info = self.participant_info[statement.name]
        assert not info.activation_stack, "explicit activation allowed only if object is inactive"

        activation = output.Activation(info.lifeline)
        activation.y = self.current_offset
        info.activation_stack.append(activation)

        self.current_offset += STATEMENT_OFFSET

    def handle_deactivation(self, statement: model.DeactivateStatement):
        info = self.participant_info[statement.name]
        assert info.activation_stack, "deactivation not possible, participant is inactive"

        activation = info.activation_stack.pop()
        activation.height = self.current_offset - activation.y

        self.current_offset += STATEMENT_OFFSET

    def handle_message(self, statement: model.MessageStatement):
        assert statement.sender != statement.receiver, "use self call syntax"
        sender_info = self.participant_info[statement.sender]
        receiver_info = self.participant_info[statement.receiver]

        if statement.activation == model.MessageActivationType.ACTIVATE:
            assert sender_info.activation_stack, "sender must be active to send a message"

            self.ensure_message_spacing(sender_info, receiver_info, output.ACTIVATION_MESSAGE_DY)
            self.activate_participant(receiver_info, sender_info)

            sender_activation = sender_info.activation_stack[-1]
            receiver_activation = receiver_info.activation_stack[-1]

            message = output.Message(sender_activation, receiver_activation, statement.text)
            message.line = statement.line
            message.arrow = statement.arrow
            message.type = output.MessageType.ACTIVATE_FROM_LEFT

        elif statement.activation == model.MessageActivationType.DEACTIVATE:
            assert sender_info.activation_stack, "sender must be active to deactivate"
            assert receiver_info.activation_stack, "receiver must be active to receive a message"

            self.ensure_message_spacing(sender_info, receiver_info, -output.ACTIVATION_MESSAGE_DY)

            sender_activation = sender_info.activation_stack[-1]
            receiver_activation = receiver_info.activation_stack[-1]

            message = output.Message(sender_activation, receiver_activation, statement.text)
            message.line = statement.line
            message.arrow = statement.arrow
            message.type = output.MessageType.DEACTIVATE_FROM_LEFT

            self.deactivate_participant(sender_info)
        else:
            raise NotImplementedError()

    def ensure_message_spacing(self, part1: ParticipantInfo, part2: ParticipantInfo, message_dy: int):
        start_gap = min(part1.index, part2.index)
        end_gap = max(part1.index, part2.index)

        max_offset = max(self.last_offset_per_gap[gap] for gap in range(start_gap, end_gap))
        current_spacing = self.current_offset - max_offset
        required_spacing = MESSAGE_MIN_SPACING - message_dy

        if current_spacing < required_spacing:
            self.current_offset += required_spacing - current_spacing

        for gap in range(start_gap, end_gap):
            self.last_offset_per_gap[gap] = self.current_offset + message_dy

    def activate_participant(self, participant: ParticipantInfo, activator: Optional[ParticipantInfo]):
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

        self.current_offset += STATEMENT_OFFSET

    def deactivate_participant(self, participant: ParticipantInfo):
        activation = participant.activation_stack.pop()
        activation.height = self.current_offset - activation.y

        self.current_offset += STATEMENT_OFFSET
