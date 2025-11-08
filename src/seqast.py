from dataclasses import dataclass
from enum import auto, Enum
from typing import List, Optional
from lark import Lark, Transformer
from pathlib import Path

from drawio import LineStyle, ArrowStyle

SCRIPT_DIR = Path(__file__).resolve().parent


class Parser:
    def __init__(self):
        with open(SCRIPT_DIR / 'syntax.lark', 'r') as f:
            grammar = f.read()

        self.lark = Lark(grammar, start='start', propagate_positions=True)

    def parse(self, text: str) -> List['Statement']:
        text = text.replace('\r', '')
        if not text.endswith('\n'):
            text += '\n'

        parsed = self.lark.parse(text)
        return SeqTransformer().transform(parsed)


class SeqTransformer(Transformer):
    @staticmethod
    def start(items):
        return consume(items)

    @staticmethod
    def statement_list(items):
        statements = []

        for item in items:
            statement = consume(item.children)
            statement.line_number = item.meta.line
            statements.append(statement)

        return statements

    @staticmethod
    def title(items):
        text = consume(items)
        return TitleStatement(text)

    @staticmethod
    def title_width(items):
        width = consume(items)
        return TitleWidthStatement(width)

    @staticmethod
    def title_height(items):
        height = consume(items)
        return TitleHeightStatement(height)

    @staticmethod
    def participant(items):
        name = consume(items)
        alias = None
        width = None
        spacing = None

        while item := consume_opt(items):
            if item.data == 'participant_alias':
                alias = str(consume(item.children))
            elif item.data == 'participant_width':
                width = int(consume(item.children))
            elif item.data == 'participant_spacing':
                spacing = int(consume(item.children))
            else:
                raise NotImplementedError()

        text = name
        name = alias or name
        return ParticipantStatement(text, name, width, spacing)

    @staticmethod
    def activation(items):
        assert len(items) > 0
        return ActivateStatement(items)

    @staticmethod
    def deactivation(items):
        assert len(items) > 0
        return DeactivateStatement(items)

    @staticmethod
    def found_message(items):
        direction_map = {
            'left': MessageDirection.LEFT,
            'right': MessageDirection.RIGHT,
        }

        direction = direction_map[str(consume(items))]
        width = consume_if(items, lambda item: isinstance(item, int))
        line, arrow, activation = consume(items)
        receiver = consume(items)
        text = consume_opt(items, default='')

        return FoundMessageStatement(direction, receiver, text, activation, line, arrow, width)

    @staticmethod
    def lost_message(items):
        direction_map = {
            'left': MessageDirection.LEFT,
            'right': MessageDirection.RIGHT,
        }

        sender = consume(items)
        line, arrow, activation = consume(items)
        direction = direction_map[consume(items)]
        width = consume_if(items, lambda item: isinstance(item, int))
        text = consume_opt(items, default='')

        return LostMessageStatement(sender, direction, text, activation, line, arrow, width)

    @staticmethod
    def message(items):
        sender = consume(items)
        line, arrow, activation = consume(items)
        receiver = consume(items)
        text = consume_opt(items, '')
        return MessageStatement(sender, receiver, text, activation, line, arrow)

    @staticmethod
    def self_call(items):
        target = consume(items)
        text = consume_opt(items)
        return MessageStatement(target, target, text, MessageActivation.REGULAR, LineStyle.SOLID, ArrowStyle.BLOCK)

    @staticmethod
    def alternative(items):
        text = consume(items)
        inner = consume(items)
        branches = []

        while branch := consume_opt(items):
            branch_text = consume_if(branch.children, lambda item: isinstance(item, str), 'else')
            branch_inner = consume(branch.children)
            branches.append(AlternativeBranch(branch_text, branch_inner))

        return AlternativeStatement(text, inner, branches)

    @staticmethod
    def option(items):
        text = consume(items)
        inner = consume(items)
        return OptionStatement(text, inner)

    @staticmethod
    def loop(items):
        text = consume(items)
        inner = consume(items)
        return LoopStatement(text, inner)

    @staticmethod
    def group(items):
        text = consume(items)
        inner = consume(items)
        return GroupStatement(text, inner)

    @staticmethod
    def note(items):
        target = consume(items)
        text = None
        dx = None
        dy = None
        width = None
        height = None

        while item := consume_opt(items):
            if item.data == 'note_text':
                text = str(consume(item.children))
            elif item.data == 'note_dx':
                dx = int(consume(item.children))
            elif item.data == 'note_dy':
                dy = int(consume(item.children))
            elif item.data == 'note_width':
                width = int(consume(item.children))
            elif item.data == 'note_height':
                height = int(consume(item.children))
            else:
                raise NotImplementedError()

        assert text is not None
        text = '<br/>'.join(line.strip() for line in text.splitlines())
        return NoteStatement(target, text, dx, dy, width, height)

    @staticmethod
    def vertical_offset(items):
        offset = consume(items)
        return VerticalOffsetStatement(offset)

    @staticmethod
    def frame_dimension(items):
        extend = consume(items)
        return ExtendFrameStatement(extend)

    @staticmethod
    def arrow(items):
        line_map = {
            '-': LineStyle.SOLID,
            '--': LineStyle.DASHED,
        }
        arrow_map = {
            '>': ArrowStyle.BLOCK,
            '>>': ArrowStyle.OPEN,
        }
        activation_map = {
            '': MessageActivation.REGULAR,
            '+': MessageActivation.ACTIVATE,
            '-': MessageActivation.DEACTIVATE,
            '|': MessageActivation.FIREFORGET,
        }

        line_str = str(consume(items))
        arrow_str = str(consume(items))
        activation_str = str(consume_opt(items, default=''))

        return line_map[line_str], arrow_map[arrow_str], activation_map[activation_str]

    @staticmethod
    def name(items):
        token = consume(items)

        if token.type == 'QUOTED_NAME':
            name = str(token)[1:-1]
        elif token.type == 'UNQUOTED_NAME':
            name = str(token)
        else:
            raise NotImplementedError()

        return name.replace('\\n', '<br/>')

    @staticmethod
    def TEXT(token):
        return str(token).replace('\\n', '<br/>')

    @staticmethod
    def NUMBER(token):
        return int(token)


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
    width: Optional[int] = None
    spacing: Optional[int] = None


@dataclass
class ActivateStatement(Statement):
    targets: List[str]


@dataclass
class DeactivateStatement(Statement):
    targets: List[str]


class MessageDirection(Enum):
    LEFT = auto()
    RIGHT = auto()


class MessageActivation(Enum):
    REGULAR = auto()
    ACTIVATE = auto()
    DEACTIVATE = auto()
    FIREFORGET = auto()


@dataclass
class MessageStatement(Statement):
    sender: str
    receiver: str
    text: str
    activation: MessageActivation
    line_style: LineStyle
    arrow_style: ArrowStyle


@dataclass
class FoundMessageStatement(Statement):
    from_direction: MessageDirection
    receiver: str
    text: str
    activation: MessageActivation
    line_style: LineStyle
    arrow_style: ArrowStyle
    width: Optional[int]


@dataclass
class LostMessageStatement(Statement):
    sender: str
    to_direction: MessageDirection
    text: str
    activation: MessageActivation
    line_style: LineStyle
    arrow_style: ArrowStyle
    width: Optional[int]


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
class GroupStatement(Statement):
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
    offset: int


@dataclass
class ExtendFrameStatement(Statement):
    extend: int


def consume(items):
    assert len(items) > 0, "missing item"
    return items.pop(0)


def consume_if(items, predicate, default=None):
    if predicate(items[0] if len(items) > 0 else None):
        return consume(items)
    else:
        return default


def consume_opt(items, default=None):
    return consume_if(items, lambda item: item is not None, default)
