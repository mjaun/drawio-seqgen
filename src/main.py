import argparse
import drawio

from seqast import Parser
from layout import Layouter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, type=str, help='Input file')
    parser.add_argument('-o', '--output', required=True, type=str, help='Output file')
    args = parser.parse_args()

    with open(args.input, 'r') as f:
        source = f.read()

    statement_list = Parser().parse(source)

    file = drawio.File()
    page = drawio.Page(file, 'Diagram')

    Layouter(page).layout(statement_list)

    file.write(args.output)


if __name__ == '__main__':
    main()
