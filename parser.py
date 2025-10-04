from lark import Lark, Transformer
from pathlib import Path

from model import SequenceDiagramDescription, ParticipantDeclaration, ActivateStatement, DeactivateStatement, \
    MessageLineStyle, MessageArrowStyle, \
    MessageActivationType, \
    MessageStatement, TitleDeclaration, SpacingStatement

SCRIPT_DIR = Path(__file__).resolve().parent


def parse(text) -> 'SequenceDiagramDescription':
    with open(SCRIPT_DIR / 'syntax.lark', 'r') as f:
        grammar = f.read()

    lark = Lark(grammar, start='start')
    parsed = lark.parse(text)
    transformed = SeqgenTransformer().transform(parsed)

    return transformed


class SeqgenTransformer(Transformer):
    def start(self, items):
        assert len(items) == 2
        declarations = list(items[0])
        statements = list(items[1])
        return SequenceDiagramDescription(declarations, statements)

    def declaration_list(self, items):
        return list(items)

    def statement_list(self, items):
        return list(items)

    def declaration(self, items):
        assert len(items) == 1
        return items[0]

    def statement(self, items):
        assert len(items) == 1
        return items[0]

    def title(self, items):
        assert len(items) == 1
        return TitleDeclaration(str(items[0]))

    def participant(self, items):
        if len(items) == 1:
            return ParticipantDeclaration(name=items[0])
        elif len(items) == 2:
            return ParticipantDeclaration(name=items[0], alias=items[1])
        else:
            raise NotImplementedError()

    def participant_alias(self, items):
        assert len(items) == 1
        return items[0]

    def activation(self, items):
        assert len(items) == 1
        return ActivateStatement(str(items[0]))

    def deactivation(self, items):
        assert len(items) == 1
        return DeactivateStatement(str(items[0]))

    def message(self, items):
        assert len(items) == 4

        sender = items[0]
        line, arrow, activation = items[1]
        receiver = items[2]
        text = items[3]

        return MessageStatement(sender, receiver, text, activation, line, arrow)

    def arrow(self, items):
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

    def name(self, items):
        assert len(items) == 1

        if items[0].type == 'QUOTED_NAME':
            return str(items[0])[1:-1]
        elif items[0].type == 'UNQUOTED_NAME':
            return str(items[0])
        else:
            raise NotImplementedError()

    def spacing(self, items):
        assert len(items) == 1
        return SpacingStatement(int(items[0]))
