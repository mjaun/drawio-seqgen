from dataclasses import dataclass
from enum import Enum, auto
from typing import List


@dataclass
class TitleDeclaration:
    text: str


@dataclass
class ParticipantDeclaration:
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
    def __init__(self, items):
        self.participants: List[ParticipantDeclaration] = []
        self.statements: List[Statement] = []
        self.title = 'Sequence Diagram'

        for item in items:
            if isinstance(item, ParticipantDeclaration):
                self.participants.append(item)
            if isinstance(item, Statement):
                self.statements.append(item)
            if isinstance(item, TitleDeclaration):
                self.title = item.text
