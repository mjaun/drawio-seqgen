from lark import Lark, Transformer
from pathlib import Path

from seqast import *
from drawio import MessageLineStyle, MessageArrowStyle

SCRIPT_DIR = Path(__file__).resolve().parent


class Parser:
    def __init__(self):
        with open(SCRIPT_DIR / 'syntax.lark', 'r') as f:
            grammar = f.read()

        self.lark = Lark(grammar, start='start')

    def parse(self, text) -> List[Statement]:
        parsed = self.lark.parse(text)
        return SeqTransformer().transform(parsed)


class SeqTransformer(Transformer):
    @staticmethod
    def start(items):
        return list(items)

    @staticmethod
    def statement_list(items):
        return list(items)

    @staticmethod
    def header_statement(items):
        assert len(items) == 1
        return items[0]

    @staticmethod
    def statement(items):
        assert len(items) == 1
        return items[0]

    @staticmethod
    def title(items):
        assert len(items) == 1
        return TitleStatement(str(items[0]))

    @staticmethod
    def title_size(items):
        assert len(items) == 2
        return TitleSizeStatement(int(items[0]), int(items[1]))

    @staticmethod
    def participant(items):
        assert len(items) in (1, 2)
        text = items[0]
        name = items[1] if len(items) == 2 else text
        return ParticipantStatement(text, name)

    @staticmethod
    def participant_alias(items):
        assert len(items) == 1
        return items[0]

    @staticmethod
    def participant_spacing(items):
        assert len(items) == 1
        return ParticipantSpacingStatement(int(items[0]))

    @staticmethod
    def participant_width(items):
        assert len(items) == 1
        return ParticipantWidthStatement(int(items[0]))

    @staticmethod
    def activation(items):
        assert len(items) == 1
        return ActivateStatement(items[0])

    @staticmethod
    def deactivation(items):
        assert len(items) == 1
        return DeactivateStatement(items[0])

    @staticmethod
    def message(items):
        assert len(items) == 4

        sender = items[0]
        line, arrow, activation = items[1]
        receiver = items[2]
        text = str(items[3])

        return MessageStatement(sender, receiver, text, activation, line, arrow)

    @staticmethod
    def self_call(items):
        assert len(items) == 2
        return SelfCallStatement(items[0], items[1])

    @staticmethod
    def self_call_width(items):
        assert len(items) == 1
        return int(items[0])

    @staticmethod
    def alternative(items):
        text = str(items[0])
        inner = items[1]
        branches = [AlternativeBranch(item[0], item[1]) for item in items[2:]]
        return AlternativeStatement(text, inner, branches)

    @staticmethod
    def alternative_else(items):
        assert len(items) == 2
        return str(items[0]), items[1]

    @staticmethod
    def option(items):
        assert len(items) == 2
        return OptionStatement(str(items[0]), items[1])

    @staticmethod
    def loop(items):
        assert len(items) == 2
        return LoopStatement(str(items[0]), items[1])

    @staticmethod
    def arrow(items):
        assert len(items) in (2, 3)

        line_map = {
            '-': MessageLineStyle.SOLID,
            '--': MessageLineStyle.DASHED,
        }
        arrow_map = {
            '>': MessageArrowStyle.BLOCK,
            '>>': MessageArrowStyle.OPEN,
        }
        activation_map = {
            '': MessageActivationType.REGULAR,
            '+': MessageActivationType.ACTIVATE,
            '-': MessageActivationType.DEACTIVATE,
            '|': MessageActivationType.FIREFORGET,
        }

        line_str = str(items[0])
        arrow_str = str(items[1])
        activation_str = str(items[2]) if len(items) > 2 else ''

        return line_map[line_str], arrow_map[arrow_str], activation_map[activation_str]

    @staticmethod
    def name(items):
        assert len(items) == 1

        if items[0].type == 'QUOTED_NAME':
            return str(items[0])[1:-1]
        elif items[0].type == 'UNQUOTED_NAME':
            return str(items[0])
        else:
            raise NotImplementedError()

    @staticmethod
    def vertical_offset(items):
        assert len(items) == 1
        return VerticalOffsetStatement(int(items[0]))

    @staticmethod
    def frame_dimension(items):
        assert len(items) == 2
        return FrameDimensionStatement(items[0], int(items[1]))
