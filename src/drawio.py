import os
import xml.etree.ElementTree as ET

from dataclasses import dataclass
from enum import auto, Enum
from typing import List, Dict, Optional

ACTIVATION_WIDTH = 10
MESSAGE_ANCHOR_DY = 5

# Live reloading in draw.io does not work well if an object ID is suddenly used for another type of object.
# On the other side, the integration test require a predictable output.
# Using deterministic IDs with a random prefix which can be overridden for testing seems like a good trade-off.
next_id = 1
id_prefix = os.getenv('SEQGEN_ID_PREFIX', os.getrandom(4).hex() + '-')


class MessageAnchor(Enum):
    NONE = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()


class MessageLineStyle(Enum):
    SOLID = auto()
    DASHED = auto()


class MessageArrowStyle(Enum):
    BLOCK = auto()
    OPEN = auto()


class TextAlignment(Enum):
    TOP_CENTER = auto()
    MIDDLE_RIGHT = auto()


@dataclass
class Point:
    x: int
    y: int


class File:
    def __init__(self):
        self.pages: List[Page] = []

    def xml(self) -> ET.Element:
        root = ET.Element("mxfile", attrib={
            'host': 'seqgen',
            'agent': 'seqgen',
            'version': '26.2.2',
        })

        for page in self.pages:
            page.xml(root)

        return root


class Page:
    def __init__(self, file: File, name: str):
        self.name = name
        self.id = create_id()
        self.objects: List[Object] = []
        file.pages.append(self)

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        diagram = ET.SubElement(xml_parent, 'diagram', attrib={
            'name': self.name,
            'id': self.id,
        })

        graph_model = ET.SubElement(diagram, 'mxGraphModel', attrib={
            'dx': '0',
            'dy': '0',
            'grid': '1',
            'gridSize': '10',
            'guides': '1',
            'tooltips': '1',
            'connect': '1',
            'arrows': '1',
            'fold': '1',
            'page': '0',
            'pageScale': '1',
            'pageWidth': '851',
            'pageHeight': '1100',
            'background': '#ffffff',
            'math': '0',
            'shadow': '0',
        })

        root = ET.SubElement(graph_model, 'root')

        ET.SubElement(root, 'mxCell', attrib={'id': '0'})
        ET.SubElement(root, 'mxCell', attrib={'id': '1', 'parent': '0'})

        for obj in self.objects:
            obj.xml(root)

        return diagram


class Object:
    def __init__(self, page: Page, parent: Optional['Object'], value: str):
        self.id = create_id()
        self.page = page
        self.parent = parent
        self.value = value
        page.objects.append(self)

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        style = ''

        for key, value in self.style().items():
            if value is not None:
                style += f'{key}={value};'
            else:
                style += f'{key};'

        attr = {
            'id': self.id,
            'value': self.value,
            'parent': self.parent.id if self.parent else '1',
            'style': style,
        }

        attr.update(self.attr())

        cell = ET.SubElement(xml_parent, 'mxCell', attrib=attr)
        return cell

    def style(self) -> Dict[str, Optional[str]]:
        return {}

    def attr(self) -> Dict[str, str]:
        return {}


class ObjectWithAbsoluteGeometry(Object):
    def __init__(self, page: Page, parent: Optional['Object'], value: str):
        super().__init__(page, parent, value)

        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0

    def center_x(self):
        return self.x + (self.width / 2)

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        cell = super().xml(xml_parent)

        ET.SubElement(cell, 'mxGeometry', attrib={
            'x': str(self.x),
            'y': str(self.y),
            'width': str(self.width),
            'height': str(self.height),
            'as': 'geometry'
        })

        return cell


class Text(ObjectWithAbsoluteGeometry):
    def __init__(self, page: Page, parent: Optional['Object'], value: str):
        super().__init__(page, parent, value)

        self.width = 100
        self.height = 20

    def attr(self) -> Dict[str, str]:
        return {
            'vertex': '1'
        }

    def style(self) -> Dict[str, Optional[str]]:
        return {
            'text': None,
            'html': '1',
            'align': 'left',
            'verticalAlign': 'middle',
            'rounded': '0',
            'labelPosition': 'center',
            'verticalLabelPosition': 'middle',
            'labelBackgroundColor': 'default',
        }


class Frame(ObjectWithAbsoluteGeometry):
    def __init__(self, page: Page, value: str):
        super().__init__(page, None, value)

        self.box_width = 160
        self.box_height = 30

    def attr(self) -> Dict[str, str]:
        return {
            'vertex': '1'
        }

    def style(self) -> Dict[str, Optional[str]]:
        return {
            'shape': 'umlFrame',
            'whiteSpace': 'wrap',
            'html': '1',
            'pointerEvents': '0',
            'width': str(self.box_width),
            'height': str(self.box_height),
        }


class Separator(Object):
    def __init__(self, frame: Frame):
        super().__init__(frame.page, None, '')

        self.frame = frame
        self.y = 0

    def attr(self) -> Dict[str, str]:
        return {
            'edge': '1',
            'source': self.frame.id,
            'target': self.frame.id,
        }

    def style(self) -> Dict[str, Optional[str]]:
        rel_y = self.y / self.frame.height

        return {
            'html': '1',
            'endArrow': 'none',
            'dashed': '1',
            'rounded': '0',
            'entryX': '1',
            'entryY': f"{rel_y:.3f}",
            'entryDx': '0',
            'entryDy': '0',
            'entryPerimeter': '0',
            'exitX': '0',
            'exitY': f"{rel_y:.3f}",
            'exitDx': '0',
            'exitDy': '0',
            'exitPerimeter': '0',
        }

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        cell = super().xml(xml_parent)

        geometry = ET.SubElement(cell, 'mxGeometry', attrib={
            'relative': '1',
            'as': 'geometry'
        })

        ET.SubElement(geometry, 'mxPoint', attrib={'as': 'targetPoint'})
        ET.SubElement(geometry, 'mxPoint', attrib={'as': 'sourcePoint'})

        return cell


class Lifeline(ObjectWithAbsoluteGeometry):
    def __init__(self, page: Page, value: str):
        super().__init__(page, None, value)

        self.width = 100
        self.height = 300

    def attr(self) -> Dict[str, str]:
        return {
            'vertex': '1'
        }

    def style(self) -> Dict[str, Optional[str]]:
        return {
            'shape': 'umlLifeline',
            'perimeter': 'lifelinePerimeter',
            'whiteSpace': 'wrap',
            'html': '1',
            'container': '1',
            'dropTarget': '0',
            'collapsible': '0',
            'recursiveResize': '0',
            'outlineConnect': '0',
            'portConstraint': 'eastwest',
            'newEdgeStyle': '{"curved":0,"rounded":0}',
        }


class Activation(Object):
    def __init__(self, lifeline: Lifeline):
        super().__init__(lifeline.page, lifeline, '')

        self.lifeline = lifeline
        self.dx = 0
        self.y = 90
        self.height = 100

    def attr(self) -> Dict[str, str]:
        return {
            'vertex': '1'
        }

    def style(self) -> Dict[str, Optional[str]]:
        return {
            'html': '1',
            'points': '[[0,0,0,0,5],[0,1,0,0,-5],[1,0,0,0,5],[1,1,0,0,-5]]',
            'perimeter': 'orthogonalPerimeter',
            'outlineConnect': '0',
            'targetShapes': 'umlLifeline',
            'portConstraint': 'eastwest',
            'newEdgeStyle': '{"curved":0,"rounded":0}',
        }

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        cell = super().xml(xml_parent)

        ET.SubElement(cell, 'mxGeometry', attrib={
            'x': str((self.lifeline.width / 2) - (ACTIVATION_WIDTH / 2) + self.dx),
            'y': str(self.y),
            'width': str(ACTIVATION_WIDTH),
            'height': str(self.height),
            'as': 'geometry'
        })

        return cell


class Message(Object):
    def __init__(self, source: Object, target: Object, value: str):
        super().__init__(source.page, None, value)
        self.source = source
        self.target = target

        self.type = MessageAnchor.NONE
        self.line = MessageLineStyle.SOLID
        self.arrow = MessageArrowStyle.BLOCK
        self.alignment = TextAlignment.TOP_CENTER
        self.points: List[Point] = []

    def attr(self) -> Dict[str, str]:
        return {
            'edge': '1',
            'source': self.source.id,
            'target': self.target.id,
        }

    def style(self) -> Dict[str, Optional[str]]:
        style = {
            'html': '1',
            'curved': '0',
            'rounded': '0',
        }

        alignment_map = {
            TextAlignment.TOP_CENTER: {
                'verticalAlign': 'bottom',
            },
            TextAlignment.MIDDLE_RIGHT: {
                'align': 'left',
                'spacingLeft': '2',
            },
        }

        arrow_map = {
            MessageArrowStyle.BLOCK: {
                'endArrow': 'block',
            },
            MessageArrowStyle.OPEN: {
                'endArrow': 'open',
            },
        }

        line_map = {
            MessageLineStyle.SOLID: {
                'dashed': '0',
            },
            MessageLineStyle.DASHED: {
                'dashed': '1',
            },
        }

        type_map = {
            MessageAnchor.NONE: {},
            MessageAnchor.TOP_LEFT: {
                'entryX': '0',
                'entryY': '0',
                'entryDx': '0',
                'entryDy': str(MESSAGE_ANCHOR_DY),
            },
            MessageAnchor.TOP_RIGHT: {
                'entryX': '1',
                'entryY': '0',
                'entryDx': '0',
                'entryDy': str(MESSAGE_ANCHOR_DY),
            },
            MessageAnchor.BOTTOM_LEFT: {
                'exitX': '0',
                'exitY': '1',
                'exitDx': '0',
                'exitDy': str(-MESSAGE_ANCHOR_DY),
            },
            MessageAnchor.BOTTOM_RIGHT: {
                'exitX': '1',
                'exitY': '1',
                'exitDx': '0',
                'exitDy': str(-MESSAGE_ANCHOR_DY),
            },
        }

        style.update(alignment_map[self.alignment])
        style.update(arrow_map[self.arrow])
        style.update(line_map[self.line])
        style.update(type_map[self.type])

        return style

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        cell = super().xml(xml_parent)

        geometry = ET.SubElement(cell, 'mxGeometry', attrib={
            'relative': '1',
            'as': 'geometry'
        })

        if self.type == MessageAnchor.NONE:
            ET.SubElement(geometry, 'mxPoint', attrib={'as': 'targetPoint'})
            ET.SubElement(geometry, 'mxPoint', attrib={'as': 'sourcePoint'})
        elif self.type in (MessageAnchor.TOP_LEFT, MessageAnchor.TOP_RIGHT):
            ET.SubElement(geometry, 'mxPoint', attrib={'as': 'sourcePoint'})
        elif self.type in (MessageAnchor.BOTTOM_LEFT, MessageAnchor.BOTTOM_RIGHT):
            ET.SubElement(geometry, 'mxPoint', attrib={'as': 'targetPoint'})
        else:
            raise NotImplementedError()

        if self.points:
            array = ET.SubElement(geometry, 'Array', attrib={'as': 'points'})

            for point in self.points:
                ET.SubElement(array, 'mxPoint', attrib={'x': str(point.x), 'y': str(point.y)})

        return cell


class Note(ObjectWithAbsoluteGeometry):
    def __init__(self, page: Page, value: str):
        super().__init__(page, None, value)

        self.width = 120
        self.height = 60

    def attr(self) -> Dict[str, str]:
        return {
            'vertex': '1'
        }

    def style(self) -> Dict[str, Optional[str]]:
        return {
            'shape': 'note',
            'whiteSpace': 'wrap',
            'html': '1',
            'backgroundOutline': '1',
            'darkOpacity': '0.05',
            'size': '10',
            'align': 'left',
            'spacing': '8',
        }


def create_id() -> str:
    global next_id
    result = next_id
    next_id += 1
    return id_prefix + str(result)
