import argparse
import drawio

import xml.etree.ElementTree as ET

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

    with open(args.output, 'w') as f:
        f.write(xml_pretty(file.xml()))


# manually pretty print output to stay compatible with Python 3.8
def xml_pretty(element: ET.Element) -> str:
    xml_str = ET.tostring(element, encoding='utf-8', xml_declaration=False).decode('utf-8')
    output = ''
    indent = 0

    for line in xml_str.replace('>', '>\n').split('\n'):
        if not line:
            continue

        if line.startswith('</'):
            indent -= 2

        output += (' ' * indent) + line + '\n'

        if not line.startswith('</') and not line.endswith('/>'):
            indent += 2

    return output


if __name__ == '__main__':
    main()
