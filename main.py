from parser import parse
from layouter import Layouter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def main():
    with open(SCRIPT_DIR / 'example.seq', 'r') as f:
        example = f.read()

    description = parse(example)

    print(description.participants)
    print(description.statements)

    file = Layouter().layout(description)

    file.write(SCRIPT_DIR / 'output.xml')
    file.write(SCRIPT_DIR / 'output.drawio')


if __name__ == '__main__':
    main()
