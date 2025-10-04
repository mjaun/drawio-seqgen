from dataclasses import dataclass
from enum import Enum, auto
from pydoc import describe
from typing import List


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
    NONE = auto()
    ACTIVATE = auto()
    DEACTIVATE = auto()


class MessageLineStyle(Enum):
    SOLID = auto()
    DASHED = auto()


class MessageArrowStyle(Enum):
    BLOCK = auto()
    OPEN = auto()


@dataclass
class MessageStatement(Statement):
    sender: str
    receiver: str
    text: str
    activation: MessageActivationType
    line: MessageLineStyle
    arrow: MessageArrowStyle


class SequenceDiagramDescription:
    def __init__(self, declarations, statements: List[Statement]):
        self.statements: List[Statement] = statements
        self.participants: List[ParticipantDeclaration] = all_of_type(ParticipantDeclaration, declarations)
        self.title = 'Sequence Diagram'

        if declaration := first_of_type(TitleDeclaration, declarations):
            self.title = declaration.text


def first_of_type(type, items):
    return next((item for item in items if isinstance(item, type)), None)


def all_of_type(type, items):
    return [item for item in items if isinstance(item, type)]
