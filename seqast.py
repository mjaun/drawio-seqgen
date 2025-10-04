from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

from drawio import MessageLineStyle, MessageArrowStyle


@dataclass
class Declaration:
    pass


@dataclass
class TitleTextDeclaration(Declaration):
    text: str


@dataclass
class TitleSizeDeclaration(Declaration):
    width: int
    height: int


@dataclass
class ParticipantDeclaration:
    pass


@dataclass
class ParticipantNameDeclaration(ParticipantDeclaration):
    text: str
    name: str


@dataclass
class ParticipantWidthDeclaration(ParticipantDeclaration):
    width: int


@dataclass
class ParticipantSpacingDeclaration(ParticipantDeclaration):
    spacing: int


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
    width: Optional[int] = None


@dataclass
class SpacingStatement(Statement):
    spacing: int


@dataclass
class OptionStatement(Statement):
    text: str
    inner: List[Statement]


@dataclass
class LoopStatement(Statement):
    text: str
    inner: List[Statement]


class SeqDescription:
    def __init__(self, declarations: List[Declaration], statements: List[Statement]):
        self.statements: List[Statement] = statements
        self.participants: List[ParticipantDeclaration] = all_of_type(ParticipantDeclaration, declarations)
        self.title: Optional[TitleTextDeclaration] = last_of_type(TitleTextDeclaration, declarations)
        self.title_size: Optional[TitleSizeDeclaration] = last_of_type(TitleSizeDeclaration, declarations)


def last_of_type(type, items):
    return next((item for item in reversed(items) if isinstance(item, type)), None)


def all_of_type(type, items):
    return list(filter(lambda item: isinstance(item, type), items))
