from lark import Lark, Transformer
from pathlib import Path

from seqast import *
from drawio import MessageLineStyle, MessageArrowStyle

SCRIPT_DIR = Path(__file__).resolve().parent


class Parser:
    def __init__(self):
        with open(SCRIPT_DIR / 'syntax.lark', 'r') as f:
            grammar = f.read()

        self.lark = Lark(grammar, start='start', propagate_positions=True)

    def parse(self, text) -> List[Statement]:
        parsed = self.lark.parse(text)
        return SeqTransformer().transform(parsed)


class SeqTransformer(Transformer):
    @staticmethod
    def start(items):
        return SeqTransformer.inner_statements(items)

    @staticmethod
    def inner_statements(items):
        statements = []

        for item in items:
            assert len(item.children) == 1
            statement = item.children[0]
            statement.line_number = item.meta.line
            statements.append(statement)

        return statements

    @staticmethod
    def title(items):
        assert len(items) == 1
        return TitleStatement(items[0])

    @staticmethod
    def title_size(items):
        assert len(items) == 2
        return TitleSizeStatement(items[0], items[1])

    @staticmethod
    def participant(items):
        assert len(items) in (1, 2)
        if len(items) == 1:
            return ParticipantStatement(items[0], items[0])
        else:
            assert len(items[1].children) == 1
            return ParticipantStatement(items[0], items[1].children[0])

    @staticmethod
    def participant_spacing(items):
        assert len(items) == 1
        return ParticipantSpacingStatement(items[0])

    @staticmethod
    def participant_width(items):
        assert len(items) == 1
        return ParticipantWidthStatement(items[0])

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
        assert len(items) in (3, 4)
        line, arrow, activation = items[1]
        text = items[3] if len(items) == 4 else ''
        return MessageStatement(items[0], items[2], text, activation, line, arrow)

    @staticmethod
    def self_call(items):
        assert len(items) == 2
        return SelfCallStatement(items[0], items[1])

    @staticmethod
    def alternative(items):
        assert len(items) == 3
        alternative = AlternativeStatement(items[0], items[1], [])

        for branch in items[2].children:
            if len(branch.children) == 1:
                alternative.branches.append(AlternativeBranch('else', branch.children[0]))
            elif len(branch.children) == 2:
                alternative.branches.append(AlternativeBranch(branch.children[0], branch.children[1]))
            else:
                raise NotImplementedError()

        return alternative

    @staticmethod
    def option(items):
        assert len(items) == 2
        return OptionStatement(items[0], items[1])

    @staticmethod
    def loop(items):
        assert len(items) == 2
        return LoopStatement(items[0], items[1])

    @staticmethod
    def note(items):
        assert len(items) == 3

        lines = items[2].children[0].splitlines()
        text = '<br/>'.join(line.strip() for line in lines)

        note = NoteStatement(items[0], text)

        for attr in items[1].children:
            if attr.data == 'note_dx':
                note.dx = int(attr.children[0])
            elif attr.data == 'note_dy':
                note.dy = int(attr.children[0])
            elif attr.data == 'note_width':
                note.width = int(attr.children[0])
            elif attr.data == 'note_height':
                note.height = int(attr.children[0])
            else:
                raise NotImplementedError()

        return note

    @staticmethod
    def vertical_offset(items):
        assert len(items) == 1
        return VerticalOffsetStatement(items[0])

    @staticmethod
    def frame_dimension(items):
        assert len(items) == 2
        return FrameDimensionStatement(items[0], items[1])

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
    def TEXT(token):
        return str(token).replace('\\n', '<br/>')

    @staticmethod
    def NUMBER(token):
        return int(token)
