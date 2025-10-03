from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class ActivationType(Enum):
    NONE = auto()
    ACTIVATE = auto()
    DEACTIVATE = auto()


class LineStyle(Enum):
    SOLID = auto()
    DASHED = auto()


class ArrowStyle(Enum):
    BLOCK = auto()
    OPEN = auto()


@dataclass
class Participant:
    name: str
    alias: str = None

    def __post_init__(self):
        if not self.alias:
            self.alias = self.name


@dataclass
class Statement:
    pass


@dataclass
class Activation(Statement):
    name: str


@dataclass
class Deactivation(Statement):
    name: str


@dataclass
class Message(Statement):
    sender: str
    receiver: str
    text: str
    activation: ActivationType
    line: LineStyle
    arrow: ArrowStyle


class SequenceDiagramDescription:
    def __init__(self, items):
        self.participants: List[Participant] = [item for item in items if isinstance(item, Participant)]
        self.statements: List[Statement] = [item for item in items if isinstance(item, Statement)]
