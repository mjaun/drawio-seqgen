import argparse
import drawio

from seqparse import Parser
from layout import Layouter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, type=str, help='Input file')
    parser.add_argument('-o', '--output', required=True, type=str, help='Output file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        example = f.read()

    statement_list = Parser().parse(example)

    file = drawio.File()
    page = drawio.Page(file, 'Diagram')

    Layouter(page).layout(statement_list)

    file.write(args.output)


if __name__ == '__main__':
    main()
