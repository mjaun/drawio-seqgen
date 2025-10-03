from dataclasses import dataclass
from typing import List, Dict, Optional

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

    def __init__(self):
        self.participant_info: Dict[str, ParticipantInfo] = {}
        self.current_y = self.sequence_start_offset

    def layout(self, description: model.SequenceDiagramDescription) -> output.File:
        file = output.File()
        page = output.Page(file, 'Diagram')

        self.create_participants(page, description)
        self.process_statements(description)
        self.finalize(page, description)

        return file

    def create_participants(self, page: output.Page, description: model.SequenceDiagramDescription):
        for index, participant in enumerate(description.participants):
            lifeline = output.Lifeline(page, participant.name)

            lifeline.width = self.lifeline_width
            lifeline.x = index * (self.lifeline_width + self.lifeline_spacing)

            self.participant_info[participant.alias] = ParticipantInfo(participant, lifeline)

    def finalize(self, page: output.Page, description: model.SequenceDiagramDescription):
        self.current_y += self.sequence_end_offset

        for participant in self.participant_info.values():
            participant.lifeline.height = self.current_y

        frame = output.Frame(page, description.title)
        frame.x = -self.frame_padding
        frame.y = -self.frame_padding - frame.header_height
        frame.width = 2 * self.frame_padding + len(description.participants) * self.lifeline_width + \
                      (len(description.participants) - 1) * self.lifeline_spacing
        frame.height = frame.header_height + 2 * self.frame_padding + self.current_y

    def process_statements(self, description: model.SequenceDiagramDescription):
        handlers = {
            model.Activation: self.handle_activation,
            model.Deactivation: self.handle_deactivation,
            model.Message: self.handle_message,
        }

        for statement in description.statements:
            if type(statement) not in handlers:
                raise NotImplementedError()

            handlers[type(statement)](statement)

    def handle_activation(self, statement: model.Activation):
        info = self.participant_info[statement.name]

        activation = output.Activation(info.lifeline)
        activation.y = self.current_y
        info.activation_stack.append(activation)

        self.current_y += self.activation_offset

    def handle_deactivation(self, statement: model.Deactivation):
        info = self.participant_info[statement.name]
        assert info.activation_stack

        activation = info.activation_stack.pop()
        activation.height = self.current_y - activation.y

        self.current_y += self.activation_offset

    def handle_message(self, statement: model.Message):
        sender_info = self.participant_info[statement.sender]
        receiver_info = self.participant_info[statement.receiver]

        if statement.activation == model.ActivationType.ACTIVATE:
            activation = output.Activation(receiver_info.lifeline)
            activation.y = self.current_y
            receiver_info.activation_stack.append(activation)

            self.current_y += self.activation_offset

            output.MessageActivate(sender_info.activation_stack[-1], activation, statement.text)

        elif statement.activation == model.ActivationType.DEACTIVATE:
            self.current_y += self.message_offset

            activation = sender_info.activation_stack.pop()
            activation.height = self.current_y - activation.y

            self.current_y += self.activation_offset

            output.MessageDeactivate(activation, receiver_info.activation_stack[-1], statement.text)
        else:
            raise NotImplementedError()


@dataclass
class ParticipantInfo:
    participant: model.Participant
    lifeline: output.Lifeline
    activation_stack: List[output.Activation] = None

    def __post_init__(self):
        if not self.activation_stack:
            self.activation_stack = []
