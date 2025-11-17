from dataclasses import dataclass
from enum import auto, Enum
from typing import List, Optional, Any
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
        return consume_next(items, 'statement_list')

    @staticmethod
    def statement_list(items):
        statements = []

        for item in items:
            statement = item.children[0]
            statement.line_number = item.meta.line
            statements.append(statement)

        return ParsedValue(statements, 'statement_list')

    @staticmethod
    def title(items):
        text = consume_next(items, 'name')
        width = consume_opt(items, 'title_width')
        height = consume_opt(items, 'title_height')
        return TitleStatement(text, width, height)

    @staticmethod
    def title_width(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'title_width')

    @staticmethod
    def title_height(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'title_height')

    @staticmethod
    def participant(items):
        text = consume_next(items, 'name')
        alias = consume_opt(items, 'participant_alias')
        width = consume_opt(items, 'participant_width')
        spacing = consume_opt(items, 'participant_spacing')
        return ParticipantStatement(text, alias or text, width, spacing)

    @staticmethod
    def participant_alias(items):
        value = consume_next(items, 'name')
        return ParsedValue(value, 'participant_alias')

    @staticmethod
    def participant_width(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'participant_width')

    @staticmethod
    def participant_spacing(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'participant_spacing')

    @staticmethod
    def activate(items):
        targets = consume_all(items, 'name')
        return ActivateStatement(targets)

    @staticmethod
    def deactivate(items):
        targets = consume_all(items, 'name')
        return DeactivateStatement(targets)

    @staticmethod
    def found_message(items):
        direction = consume_next(items, 'direction')
        width = consume_next_opt(items, 'NUMBER')
        line, arrow, activation = consume_next(items, 'arrow')
        receiver = consume_next(items, 'name')
        text = consume_next_opt(items, 'TEXT', default='')
        return FoundMessageStatement(direction, receiver, text, activation, line, arrow, width)

    @staticmethod
    def lost_message(items):
        sender = consume_next(items, 'name')
        line, arrow, activation = consume_next(items, 'arrow')
        direction = consume_next(items, 'direction')
        width = consume_next_opt(items, 'NUMBER')
        text = consume_next_opt(items, 'TEXT', default='')
        return LostMessageStatement(sender, direction, text, activation, line, arrow, width)

    @staticmethod
    def DIRECTION(token):
        direction_map = {
            'left': MessageDirection.LEFT,
            'right': MessageDirection.RIGHT,
        }

        value = direction_map[str(token)]
        return ParsedValue(value, 'direction')

    @staticmethod
    def message(items):
        sender = consume_next(items, 'name')
        line, arrow, activation = consume_next(items, 'arrow')
        receiver = consume_next(items, 'name')
        text = consume_next_opt(items, 'TEXT', default='')
        return MessageStatement(sender, receiver, text, activation, line, arrow)

    @staticmethod
    def self_call(items):
        target = consume_next(items, 'name')
        text = consume_next_opt(items, 'TEXT', default='')
        return MessageStatement(target, target, text, MessageActivation.REGULAR, LineStyle.SOLID, ArrowStyle.BLOCK)

    @staticmethod
    def alternative(items):
        text = consume_next(items, 'TEXT')
        inner = consume_next(items, 'statement_list')
        branches = consume_all(items, 'alternative_branch')
        return AlternativeStatement(text, inner, branches)

    @staticmethod
    def alternative_branch(items):
        text = consume_next_opt(items, 'TEXT', default='else')
        inner = consume_next(items, 'statement_list')
        return ParsedValue(AlternativeBranch(text, inner), 'alternative_branch')

    @staticmethod
    def option(items):
        text = consume_next(items, 'TEXT')
        inner = consume_next(items, 'statement_list')
        return OptionStatement(text, inner)

    @staticmethod
    def loop(items):
        text = consume_next(items, 'TEXT')
        inner = consume_next(items, 'statement_list')
        return LoopStatement(text, inner)

    @staticmethod
    def group(items):
        text = consume_next(items, 'TEXT')
        inner = consume_next(items, 'statement_list')
        return GroupStatement(text, inner)

    @staticmethod
    def note(items):
        target = consume_next(items, 'name')
        dx = consume_opt(items, 'note_dx')
        dy = consume_opt(items, 'note_dy')
        width = consume_opt(items, 'note_width')
        height = consume_opt(items, 'note_height')
        text = consume_next(items, 'note_text')

        assert text is not None
        text = '<br/>'.join(line.strip() for line in text.splitlines())
        return NoteStatement(target, text, dx, dy, width, height)

    @staticmethod
    def note_text(items):
        assert len(items) == 1
        return ParsedValue(str(items[0]), 'note_text')

    @staticmethod
    def note_dx(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'note_dx')

    @staticmethod
    def note_dy(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'note_dy')

    @staticmethod
    def note_width(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'note_width')

    @staticmethod
    def note_height(items):
        value = consume_next(items, 'NUMBER')
        return ParsedValue(value, 'note_height')

    @staticmethod
    def vertical_offset(items):
        offset = consume_next(items, 'NUMBER')
        return VerticalOffsetStatement(offset)

    @staticmethod
    def frame_dimension(items):
        extend = consume_next(items, 'NUMBER')
        return ExtendFrameStatement(extend)

    @staticmethod
    def arrow(items):
        line = consume_next(items, 'ARROW_LINE')
        arrow = consume_next(items, 'ARROW_END')
        activation = consume_next_opt(items, 'arrow_activation', MessageActivation.REGULAR)
        return ParsedValue((line, arrow, activation), 'arrow')

    @staticmethod
    def ARROW_LINE(token):
        line_map = {
            '-': LineStyle.SOLID,
            '--': LineStyle.DASHED,
        }

        return ParsedValue(line_map[str(token)], 'ARROW_LINE')

    @staticmethod
    def ARROW_END(token):
        arrow_map = {
            '>': ArrowStyle.BLOCK,
            '>>': ArrowStyle.OPEN,
        }

        return ParsedValue(arrow_map[str(token)], 'ARROW_END')

    @staticmethod
    def ARROW_ACTIVATION(token):
        activation_map = {
            '+': MessageActivation.ACTIVATE,
            '-': MessageActivation.DEACTIVATE,
            '|': MessageActivation.FIREFORGET,
        }

        return ParsedValue(activation_map[str(token)], 'arrow_activation')

    @staticmethod
    def name(items):
        value = consume_next_opt(items, 'QUOTED_NAME') or consume_next_opt(items, 'UNQUOTED_NAME')
        value = value.replace('\\n', '<br/>')
        return ParsedValue(value, 'name')

    @staticmethod
    def QUOTED_NAME(token):
        return ParsedValue(str(token)[1:-1], 'QUOTED_NAME')

    @staticmethod
    def UNQUOTED_NAME(token):
        return ParsedValue(str(token), 'UNQUOTED_NAME')

    @staticmethod
    def TEXT(token):
        value = str(token).replace('\\n', '<br/>')
        return ParsedValue(value, 'TEXT')

    @staticmethod
    def NUMBER(token):
        return ParsedValue(int(token), 'NUMBER')


@dataclass
class Statement:
    def __init__(self):
        self.line_number = 0


@dataclass
class TitleStatement(Statement):
    text: str
    width: Optional[int] = None
    height: Optional[int] = None


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


@dataclass
class ParsedValue:
    value: Any
    type: str


def consume_next(items, expected_type):
    assert len(items) > 0, "missing item"
    assert isinstance(items[0], ParsedValue), f"unparsed value: {items[0]}"
    assert items[0].type == expected_type, f"expected '{expected_type}' found '{items[0].type}'"
    return items.pop(0).value


def consume_next_opt(items, expected_type, default=None):
    if len(items) == 0:
        return default

    assert isinstance(items[0], ParsedValue), f"unparsed value: {items[0]}"
    return items.pop(0).value if items[0].type == expected_type else default


def consume_opt(items, expected_type, default=None):
    for item in items:
        assert isinstance(item, ParsedValue), f"unparsed value: {items[0]}"

        if item.type == expected_type:
            items.remove(item)
            return item.value

    return default


def consume_all(items, expected_type):
    found = []
    for item in items:
        assert isinstance(item, ParsedValue), f"unparsed value: {items[0]}"

        if item.type == expected_type:
            found.append(item)

    items[:] = [item for item in items if item not in found]
    return [item.value for item in found]
