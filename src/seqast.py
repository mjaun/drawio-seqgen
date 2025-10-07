from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

from drawio import MessageLineStyle, MessageArrowStyle


@dataclass
class Statement:
    def __init__(self):
        self.line_number = 0


@dataclass
class TitleStatement(Statement):
    text: str


@dataclass
class TitleWidthStatement(Statement):
    width: int


@dataclass
class TitleHeightStatement(Statement):
    height: int


@dataclass
class ParticipantStatement(Statement):
    text: str
    name: str


@dataclass
class ParticipantWidthStatement(Statement):
    width: int


@dataclass
class ParticipantSpacingStatement(Statement):
    spacing: int


@dataclass
class ActivateStatement(Statement):
    target: str


@dataclass
class DeactivateStatement(Statement):
    target: str


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
    line_style: MessageLineStyle
    arrow_style: MessageArrowStyle


@dataclass
class SelfCallStatement(Statement):
    target: str
    text: str


@dataclass
class AlternativeBranch:
    text: str
    inner: List[Statement]


@dataclass
class AlternativeStatement(Statement):
    text: str
    inner: List[Statement]
    branches: List[AlternativeBranch]


@dataclass
class OptionStatement(Statement):
    text: str
    inner: List[Statement]


@dataclass
class LoopStatement(Statement):
    text: str
    inner: List[Statement]


@dataclass
class NoteStatement(Statement):
    target: str
    text: str
    dx: Optional[int] = None
    dy: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class VerticalOffsetStatement(Statement):
    spacing: int


@dataclass
class FrameDimensionStatement(Statement):
    target: str
    dx: int
