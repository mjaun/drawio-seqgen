from dataclasses import dataclass
from typing import List, Dict

import model
import output


class Layouter:
    lifeline_width = 120
    lifeline_spacing = 40

    frame_padding = 30

    sequence_start_offset = 60
    sequence_end_offset = 20

    activation_offset = 10
    message_offset = 20

    def __init__(self, description: model.SequenceDiagramDescription):
        self.description = description
        self.participant_info: Dict[str, ParticipantInfo] = {}
        self.current_y = self.sequence_start_offset
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

            lifeline.width = self.lifeline_width
            lifeline.x = index * (self.lifeline_width + self.lifeline_spacing)

            end_x = lifeline.x + self.lifeline_width

            self.participant_info[participant.alias] = ParticipantInfo(participant, lifeline)

        self.frame.value = self.description.title
        self.frame.x = -self.frame_padding
        self.frame.y = -self.frame_padding - self.frame.header_height
        self.frame.width = end_x + 2 * self.frame_padding

    def finalize(self):
        self.current_y += self.sequence_end_offset

        for participant in self.participant_info.values():
            participant.lifeline.height = self.current_y

        self.frame.height = (self.current_y - self.frame.y) + self.frame_padding

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
        activation.y = self.current_y
        info.activation_stack.append(activation)

    def handle_deactivation(self, statement: model.DeactivateStatement):
        info = self.participant_info[statement.name]
        assert info.activation_stack, "deactivation not possible, participant is inactive"

        activation = info.activation_stack.pop()
        activation.height = self.current_y - activation.y

    def handle_message(self, statement: model.MessageStatement):
        assert statement.sender != statement.receiver, "use self call syntax"
        sender_info = self.participant_info[statement.sender]
        receiver_info = self.participant_info[statement.receiver]

        if statement.activation == model.MessageActivationType.ACTIVATE:
            self.current_y += self.message_offset

            activation = output.Activation(receiver_info.lifeline)
            activation.y = self.current_y
            receiver_info.activation_stack.append(activation)

            assert sender_info.activation_stack, "sender must be active to send a message"
            message = output.Message(sender_info.activation_stack[-1], activation, statement.text)
            message.line = statement.line
            message.arrow = statement.arrow
            message.type = output.MessageType.ACTIVATE_FROM_LEFT

        elif statement.activation == model.MessageActivationType.DEACTIVATE:
            self.current_y += self.message_offset

            activation = sender_info.activation_stack.pop()
            activation.height = self.current_y - activation.y

            assert receiver_info.activation_stack, "receiver must be active to deactivate"
            message = output.Message(activation, receiver_info.activation_stack[-1], statement.text)
            message.line = statement.line
            message.arrow = statement.arrow
            message.type = output.MessageType.DEACTIVATE_FROM_LEFT

        else:
            raise NotImplementedError()


@dataclass
class ParticipantInfo:
    participant: model.ParticipantDeclaration
    lifeline: output.Lifeline
    activation_stack: List[output.Activation] = None

    def __post_init__(self):
        if not self.activation_stack:
            self.activation_stack = []
