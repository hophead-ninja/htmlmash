"""htmlmash - Python based, objective html template engine and document builder library.
"""
import sys
import types

from htmlmash import _importer, _element
from htmlmash._element import Element
from htmlmash._importer import load_template

__all__ = ["Element"]


importer_enabled = True
importer_source_suffix = '.hpy'
importer_bytecode_suffix = '.hpyc'

class Module(types.ModuleType):
    def __init__(self):
        super().__init__(__name__)
        self.__dict__.update(globals())

    def __getattribute__(self, item):
        return super().__getattribute__(item)

    def __getattr__(self, item):
        from htmlmash._element import Element
        return Element.builder(item)

    @property
    def importer_enabled(self):
        return _importer.finder in sys.meta_path

    @importer_enabled.setter
    def importer_enabled(self, value):
        if value and _importer.TemplateFinder not in sys.meta_path:
            sys.meta_path.insert(0, _importer.TemplateFinder)
        elif _importer.TemplateFinder in sys.meta_path:
            sys.meta_path.remove(_importer.TemplateFinder)

    @property
    def importer_source_suffix(self):
        return _importer.SOURCE_SUFFIX

    @importer_source_suffix.setter
    def importer_source_suffix(self, value):
        assert isinstance(value, str)
        _importer.SOURCE_SUFFIX = value

    @property
    def importer_bytecode_suffix(self):
        return _importer.BYTECODE_SUFFIX

    @importer_bytecode_suffix.setter
    def importer_bytecode_suffix(self, value):
        assert isinstance(value, str)
        _importer.BYTECODE_SUFFIX = value

sys.modules[__name__] = Module()
