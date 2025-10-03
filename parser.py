from dataclasses import dataclass
from enum import Enum, auto
from lark import Lark, Transformer
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def parse(text):
    with open(SCRIPT_DIR / 'syntax.lark', 'r') as f:
        grammar = f.read()

    lark = Lark(grammar, start='start')

    parsed = lark.parse(text)
    transformed = MermaidTransformer().transform(parsed)

    print(transformed)

    return transformed


class MermaidTransformer(Transformer):
    def start(self, items):
        return list(items)

    def statement(self, items):
        assert len(items) == 1
        return items[0]

    def participant(self, items):
        if len(items) == 1:
            return Participant(name=items[0])
        elif len(items) == 2:
            return Participant(name=items[0], alias=items[1])
        else:
            raise NotImplementedError()

    def participant_alias(self, items):
        assert len(items) == 1
        return items[0]

    def activation(self, items):
        assert len(items) == 1
        return Activation(str(items[0]))

    def deactivation(self, items):
        assert len(items) == 1
        return Deactivation(str(items[0]))

    def message(self, items):
        assert len(items) == 4

        sender = items[0]
        line, arrow, activation = items[1]
        receiver = items[2]
        text = items[3]

        return Message(sender, receiver, text, activation, line, arrow)

    def arrow(self, items):
        assert len(items) in (2, 3)

        line_map = {
            '-': LineStyle.SOLID,
            '--': LineStyle.DASHED,
        }
        arrow_map = {
            '>': ArrowStyle.BLOCK,
            '>>': ArrowStyle.OPEN,
        }
        activation_map = {
            '': MessageActivation.NONE,
            '+': MessageActivation.ACTIVATE,
            '-': MessageActivation.DEACTIVATE,
        }

        line_str = str(items[0])
        arrow_str = str(items[1])
        activation_str = str(items[2]) if len(items) > 2 else ''

        return line_map[line_str], arrow_map[arrow_str], activation_map[activation_str]

    def name(self, items):
        assert len(items) == 1

        if items[0].type == 'QUOTED_NAME':
            return str(items[0])[1:-1]
        elif items[0].type == 'UNQUOTED_NAME':
            return str(items[0])
        else:
            raise NotImplementedError()


class MessageActivation(Enum):
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
class Message:
    sender: str
    receiver: str
    text: str
    activation: MessageActivation
    line: LineStyle
    arrow: ArrowStyle


@dataclass
class Activation:
    name: str


@dataclass
class Deactivation:
    name: str
