from dataclasses import dataclass
from enum import Enum, auto
from typing import List

from drawio import MessageLineStyle, MessageArrowStyle


@dataclass
class Declaration:
    pass


@dataclass
class TitleDeclaration(Declaration):
    text: str


@dataclass
class ParticipantDeclaration(Declaration):
    name: str
    alias: str = None

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name


@dataclass
class Statement:
    pass


@dataclass
class ActivateStatement(Statement):
    name: str


@dataclass
class DeactivateStatement(Statement):
    name: str


class MessageActivationType(Enum):
    REGULAR = auto()
    ACTIVATE = auto()
    DEACTIVATE = auto()
    FIREFORGET = auto()


@dataclass
class MessageStatement(Statement):
    sender: str
    receiver: str
    text: str
    activation: MessageActivationType
    line: MessageLineStyle
    arrow: MessageArrowStyle


@dataclass
class SelfCallStatement(Statement):
    name: str
    text: str


@dataclass
class SpacingStatement(Statement):
    spacing: int


class SeqDescription:
    def __init__(self, declarations, statements: List[Statement]):
        self.statements: List[Statement] = statements
        self.participants: List[ParticipantDeclaration] = all_of_type(ParticipantDeclaration, declarations)
        self.title = 'Sequence Diagram'

        if title_declaration := last_of_type(TitleDeclaration, declarations):
            self.title = title_declaration.text


def last_of_type(type, items):
    return next((item for item in reversed(items) if isinstance(item, type)), None)


def all_of_type(type, items):
    return list(filter(lambda item: isinstance(item, type), items))
