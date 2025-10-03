from parser import parse
from output import File, Page, Lifeline, Activation, MessageActivate, MessageDeactivate
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def main():
    with open(SCRIPT_DIR / 'example.seq', 'r') as f:
        example = f.read()

    parsed = parse(example)

    print(parsed)

    file = File()
    page = Page(file, 'Page-1')

    lifeline1 = Lifeline(page, ':Alice')
    lifeline1.x = 0
    activation1 = Activation(lifeline1)

    lifeline2 = Lifeline(page, ':John')
    lifeline2.x = 200
    activation2 = Activation(lifeline2)

    MessageActivate(activation1, activation2, 'dispatch')
    MessageDeactivate(activation2, activation1, 'return')

    file.write(SCRIPT_DIR / 'output.xml')
    file.write(SCRIPT_DIR / 'output.drawio')


if __name__ == '__main__':
    main()
