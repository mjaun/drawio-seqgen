import xml.etree.ElementTree as ET

from typing import List, Dict, Optional, Callable, Union


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

    def write(self, file):
        root = self.xml()
        tree = ET.ElementTree(root)
        tree.write(file, encoding='utf-8', xml_declaration=False)


class Page:
    def __init__(self, file: File, name: str):
        self.name = name
        self.id = str(id(self))
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
            'pageWidth': '850',
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
        self.id = str(id(self))
        self.page = page
        self.parent = parent
        self.value = value
        page.objects.append(self)

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        attr = {
            'id': self.id,
            'value': self.value,
            'parent': self.parent.id if self.parent else '1',
            'style': ';'.join(f'{key}={value}' for key, value in self.style().items()) + ';',
        }

        attr.update(self.attr())

        cell = ET.SubElement(xml_parent, 'mxCell', attrib=attr)
        return cell

    def style(self) -> Dict[str, str]:
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


class Lifeline(ObjectWithAbsoluteGeometry):
    def __init__(self, page: Page, value: str):
        super().__init__(page, None, value)

        self.width = 100
        self.height = 300

    def attr(self) -> Dict[str, str]:
        return {
            'vertex': '1'
        }

    def style(self) -> Dict[str, str]:
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
    def __init__(self, parent: Lifeline):
        super().__init__(parent.page, parent, '')

        self.y = 90
        self.width = 10
        self.height = 100

    def attr(self):
        return {
            'vertex': '1'
        }

    def style(self):
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

        assert isinstance(self.parent, Lifeline)

        ET.SubElement(cell, 'mxGeometry', attrib={
            'x': str((self.parent.width / 2) - (self.width / 2)),
            'y': str(self.y),
            'width': str(self.width),
            'height': str(self.height),
            'as': 'geometry'
        })

        return cell


class MessageActivate(Object):
    def __init__(self, source: Object, target: Object, value: str):
        super().__init__(source.page, None, value)
        self.source = source
        self.target = target

    def attr(self):
        return {
            'edge': '1',
            'source': self.source.id,
            'target': self.target.id,
        }

    def style(self):
        return {
            'html': '1',
            'verticalAlign': 'bottom',
            'endArrow': 'block',
            'curved': '0',
            'rounded': '0',
            'entryX': '0',
            'entryY': '0',
            'entryDx': '0',
            'entryDy': '5',
        }

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        cell = super().xml(xml_parent)

        geometry = ET.SubElement(cell, 'mxGeometry', attrib={
            'relative': '1',
            'as': 'geometry'
        })

        ET.SubElement(geometry, 'mxPoint', attrib={
            'as': 'sourcePoint'
        })

        return cell


class MessageDeactivate(Object):
    def __init__(self, source: Object, target: Object, value: str):
        super().__init__(source.page, None, value)
        self.source = source
        self.target = target

    def attr(self):
        return {
            'edge': '1',
            'source': self.source.id,
            'target': self.target.id,
        }

    def style(self):
        return {
            'html': '1',
            'verticalAlign': 'bottom',
            'endArrow': 'open',
            'dashed': '1',
            'endSize': '8',
            'curved': '0',
            'rounded': '0',
            'exitX': '0',
            'exitY': '1',
            'exitDx': '0',
            'exitDy': '-5',
        }

    def xml(self, xml_parent: ET.Element) -> ET.Element:
        cell = super().xml(xml_parent)

        geometry = ET.SubElement(cell, 'mxGeometry', attrib={
            'relative': '1',
            'as': 'geometry'
        })

        ET.SubElement(geometry, 'mxPoint', attrib={
            'as': 'targetPoint'
        })

        return cell
