import html
from htmlmash._importer import TemplateModule


VOID_ELEMENTS = ["area", "base", "br", "col", "embed", "hr", "img", "input",
                     "keygen", "link", "meta", "param", "source", "track", "wbr"]
RAW_TEXT_ELEMENTS = ["script", "style"]
ESCAPABLE_RAW_TEXT_ELEMENTS = ["textarea", "title"]


class Element:
    """An HTML element.
    """
    __slots__ = ("tag", "text", "tail", "attributes", "_children")
    __builders = {}

    def __init__(self, tag=None, *content, **attributes):
        self.tag = tag
        self.text = ""
        self.tail = ""
        self._children = []
        self.attributes = {k.strip("_"): v for k, v in attributes.items()}

        self.extend(content)

    def __call__(self, *content, **attributes):
        self.extend(content)
        self.attributes.update({k.strip("_"): v for k, v in attributes.items()})
        return self

    def __str__(self):
        return _serialize_element(self)

    def __getitem__(self, item):
        return self._children[item]

    def __iter__(self):
        for child in self._children:
            if isinstance(child, TemplateModule):
                child = child.__template__
            if not isinstance(child, Element) and hasattr(child, "__call__"):
                child = child()
                if isinstance(child, (str, bytes)):
                    child = Element(None, child)
            if not isinstance(child, Element) and hasattr(child, "__iter__"):
                for _child in iter(child):
                    yield _child
            if isinstance(child, Element):
                yield child

    def __bool__(self):
        return True if self._children else False

    def __len__(self):
        return len(self._children)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @staticmethod
    def _is_subelement(element):
        return isinstance(element, (Element, TemplateModule)) or hasattr(element, "__call__")

    def append(self, subelement):
        """Add subelement
        :param subelement: instance of Element or callable object
        :return:
        """
        if isinstance(subelement, (list,  tuple)):
            self.extend(subelement)
        elif isinstance(subelement, (str, bytes)):
            if isinstance(subelement, bytes):
                subelement = subelement.decode()
            else:
                subelement = html.escape(subelement, False)
            if self:
                self[-1].tail += subelement
            else:
                self.text += subelement
        else:
            if not isinstance(subelement, Element):
                _subelement = subelement
                subelement = Element(None)
                subelement._children.append(_subelement)
            self._children.append(subelement)

    def insert(self, index, subelement):
        """Insert subelement into this element at given position.
        :param index: Position to insert.
        :param subelement: element or callable object.
        :return:
        """
        self._is_subelement(subelement)
        self._children.insert(index, subelement)

    def extend(self, content):
        for content_element in content:
            self.append(content_element)

    def set(self, key, value):
        self.attributes[key] = value

    def get(self, key, default=None):
        return self.attributes[key] if key in self.attributes else default

    @classmethod
    def from_template_module(cls, template_module):
        return template_module.__template__

    @classmethod
    def builder(cls, tag):
        tag = tag.strip("_")
        if tag not in cls.__builders:
            cls.__builders[tag] = lambda *content, **attributes: Element(tag, *content, **attributes)
        return cls.__builders[tag]


def _serialize_element(element):
    if not isinstance(element, Element):
        return ""

    output = ""
    tag = element.tag
    text = element.text
    tail = element.tail
    if tag is not None:
        output += "<{}".format(tag)
        for key, value in element.attributes.items():
            if isinstance(value, bool):
                if value:
                    output += " {}".format(key)
            else:
                output += ' {}="{}"'.format(key, html.escape(str(value)))
        output += ">"
        if tag.lower() not in VOID_ELEMENTS:
            if text:
                output += element.text
            output += "".join(str(e) for e in element)
            output += '</{}>'.format(tag)
        if tail:
            output += html.escape(tail, False)
        return output
    else:
        doctype = element.get("doctype")

        if doctype:
            output += "<!DOCTYPE {}>".format(element.attributes["doctype"])
        if text:
            output += text
        output += "".join(str(e) for e in element)
        if tail:
            output += tail
        return output
