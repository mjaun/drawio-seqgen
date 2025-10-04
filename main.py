import argparse

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

    description = Parser().parse(example)
    file = Layouter(description).layout()

    file.write(args.output)


if __name__ == '__main__':
    main()
