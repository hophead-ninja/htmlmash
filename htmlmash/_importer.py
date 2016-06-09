import ast
import builtins
import sys
import types

import importlib.util
import importlib.machinery
import importlib.abc
from importlib import machinery


# Module #############################################################

class TemplateModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)

        from htmlmash import Element
        self.Element = Element
        self.__template__ = Element(None)

    def __str__(self):
        return str(self.__template__)

    def __repr__(self):
        name = self.__name__
        return "<TemplateModule{} from '{}'>".format(" '{}'".format(name) if name else name, self.__file__)

    def __call__(self, **kwargs):
        template = self.__loader__.create_module(self.__spec__)
        template.__dict__.update(kwargs)
        template.__loader__.exec_module(template)
        return template


def _fix_missing_fields(module):
    if "__doctype__" in module.__dict__:
        module.__template__.set("doctype", module.__dict__["__doctype__"])


# Importer ###########################################################

SOURCE_SUFFIX = ".hpy"
BYTECODE_SUFFIX = ".hpyc"


def _call_with_frames_removed(f, *args, **kwargs):
        return f(*args, **kwargs)


class TemplateLoader(importlib.machinery.SourceFileLoader):
    def create_module(self, spec):
        module = TemplateModule(spec.name)

        module.__spec__ = spec
        module.__name__ = spec.name
        module.__loader__ = spec.loader
        module.__package__ = spec.parent
        if spec.submodule_search_locations is not None:
            module.__path__ = spec.submodule_search_locations
        if spec.has_location:
            module.__file__ = spec.origin
            if spec.cached is not None:
                module.__cached__ = spec.cached

        return module

    def exec_module(self, module):
        #Yes, i'm too lazy to rewrite get_code
        importlib.machinery.BYTECODE_SUFFIXES.insert(0, BYTECODE_SUFFIX)
        code = self.get_code(module.__name__)
        importlib.machinery.BYTECODE_SUFFIXES.remove(BYTECODE_SUFFIX)

        if code is None:
            raise ImportError('cannot load module {!r} when get_code() '
                              'returns None'.format(module.__name__))

        _call_with_frames_removed(exec, code, module.__dict__)
        _fix_missing_fields(module)

    def source_to_code(self, data, path, *, _optimize=-1):
        source = importlib.util.decode_source(data)
        tree = _call_with_frames_removed(compile, source, path, 'exec', dont_inherit=True,
                                         optimize=_optimize, flags=ast.PyCF_ONLY_AST)
        tree = TemplateTransformer(self.name).transform(tree)

        return _call_with_frames_removed(compile, tree, path, 'exec',
                                         dont_inherit=False, optimize=_optimize)


def load_template(file, name=""):
    loader = TemplateLoader(name, file)
    spec = machinery.ModuleSpec(name, loader, origin=file)
    spec.has_location = True
    template = loader.create_module(spec)
    loader.exec_module(template)
    return template


class TemplateFinder:
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if path is None:
            path = sys.path
        for _path in path:
            finder = importlib.machinery.FileFinder(_path, (TemplateLoader, [SOURCE_SUFFIX]))
            spec = finder.find_spec(fullname)
            if spec is not None and isinstance(spec.loader, TemplateLoader):
                break
        else:
            spec = None
        return spec
sys.meta_path.insert(0, TemplateFinder)


# AST ################################################################

class TemplateTransformer(ast.NodeTransformer):
    def __init__(self, template_name):
        self.template_name = template_name
        self.names = []
        self.ids = []

    def transform(self, node):
        node = super().visit(node)
        node = self._visit_Module(node)
        ast.fix_missing_locations(node)
        return node

    # Global Visitors

    def visit_Import(self, import_node):
        for alias in import_node.names:
            name = alias.asname if alias.asname is not None else alias.name
            if name not in self.names:
                self.names.append(name)
        return import_node

    def visit_ImportFrom(self, import_node):
        for alias in import_node.names:
            name = alias.asname if alias.asname is not None else alias.name
            if name not in self.names:
                self.names.append(name)
        return import_node


    def visit_Assign(self, assign_node):
        for node in assign_node.targets:
            if "id" in node._fields and node.id not in self.names:
                self.names.append(node.id)
        return assign_node

    def visit_Call(self, call_node):
        def search(node):
            if isinstance(node, list):
                for _node in node:
                    search(_node)
            if isinstance(node, ast.AST):
                if isinstance(node, ast.Call):
                    func = node.func
                    if "id" in func._fields and func.id not in self.ids and func.id \
                            not in self.names and func.id not in builtins.__dict__:
                        self.ids.append(func.id)
                        args = []
                        for arg in node.args:
                            if isinstance(arg, (ast.IfExp, ast.GeneratorExp)):
                                arg = self._wrap_lambda(arg)
                            args.append(arg)
                        node.args = args
                    if not isinstance(func, ast.Attribute):
                        search(node.args)
                for field in [getattr(node, f) for f in node._fields]:
                    search(field)
        search(call_node)
        return call_node

    def _visit_FunctionDef(self, func_node, element_name='__template__'):
        body = []
        for node in func_node.body:
            if isinstance(node, ast.With) and len(node.items) == 1:
                item = node.items[0]
                if isinstance(item.context_expr, ast.Call):
                    func = item.context_expr.func
                    if isinstance(func, ast.Name) and func.id == "Element":
                        node = self._visit_With(node, element_name)
            body.append(node)

        func_node.body = body
        return func_node

    # Template Scope Visitors

    def _visit_Assign(self, assign_node, dummy=None):
        def search_ids(node):
            ids = []
            for elt in node.elts:
                if isinstance(elt, ast.Name):
                    ids.append(elt.id)
                else:
                    ids.extend(search_ids(elt))
            return ids

        nodes = []
        for idx, target in enumerate(assign_node.targets):
            target_ids = []
            if not isinstance(target, ast.Name):
                target_ids.append(search_ids(target))
            else:
                target_ids.append([target.id])
            compares = []
            for ids in target_ids:
                target_compares = []
                for _id in ids:
                    compare = ast.Compare(left=ast.Str(s=_id), ops=[ast.NotIn()],
                                          comparators=[ast.Call(
                                              func=ast.Name(id="globals", ctx=ast.Load()),
                                              args=[], keywords=[])])
                    target_compares.append(compare)
                compares.append(target_compares)

            for target_compares in compares:
                if len(target_compares) == 1:
                    test = target_compares[0]
                    new_target = [assign_node.targets[0]]
                else:
                    test = ast.BoolOp(op=ast.Or(), values=target_compares)
                    new_target = [assign_node.targets[idx]]
                new_assign = ast.Assign(targets=new_target, value=assign_node.value)
                nodes.append(ast.If(test=test, body=[new_assign], orelse=[]))
        return nodes

    def _visit_ImportFrom(self, importfrom_node):
        if importfrom_node.names[0].name == "*":
            raise SyntaxError("import * is not allowed in template scope, '{}' template".format(self.template_name))
        return importfrom_node

    def _visit_Module(self, module_node):
        if self.ids:
            self.ids.append("Element")
            import_node = ast.ImportFrom(module='htmlmash',
                                         names=[ast.alias(name=n, asname=None) for n in self.ids], level=0)
            body = [import_node]
        else:
            body = []
        for node in module_node.body:
            method = '_visit_' + node.__class__.__name__
            visitor = getattr(self, method, None)
            if visitor is not None:
                node = visitor(node)
            if not isinstance(node, ast.AST):
                body.extend(node)
            else:
                body.append(node)
        module_node.body = body
        return module_node

    def _visit_Expr(self, expr_node, element_name='__template__'):
        func_node = ast.Attribute(value=ast.Name(id=element_name, ctx=ast.Load()), attr='append', ctx=ast.Load())
        expr_value = expr_node.value
        if isinstance(expr_value, (ast.IfExp, ast.GeneratorExp)):
            expr_value = self._wrap_lambda(expr_value)
        if isinstance(expr_value, ast.Call):
            def search_str(node):
                if isinstance(node, ast.Str):
                    return True
                if isinstance(node, ast.Attribute):
                    return search_str(node.value)
                if isinstance(node, ast.Call):
                    return search_str(node.func)
                return False

            if search_str(expr_value):
                expr_value = self._wrap_lambda(expr_value)

        new_node = ast.Expr(value=ast.Call(func=func_node, args=[expr_value], keywords=[]))
        return ast.copy_location(new_node, expr_node)

    def _visit_Tuple(self, tuple_node, dummy=None):
        elts = []
        for elt in tuple_node.elts:
            if isinstance(elt, (ast.IfExp, ast.GeneratorExp)):
                elt = self._wrap_lambda(elt)
            elts.append(elt)
        tuple_node.elts = elts
        return tuple_node

    def _visit_With(self, with_node, element_name='__template__'):
        def search_ids(node):
            ids = []
            for elt in node.elts:
                if isinstance(elt, ast.Name):
                    ids.append(elt.id)
                else:
                    ids.extend(search_ids(elt))
            return ids

        if len(with_node.items) > 1:
            raise SyntaxError("'with' may contain one item in template scope, '{}' template".format(self.template_name))
        else:
            item = with_node.items[0]
            # if item.optional_vars:
            #     raise SyntaxError("optional 'with' args 'as...' are not supported in template scope,"
            #                       " '{}' template".format(self.template_name))
            if isinstance(item.context_expr, ast.Call):
                call = item.context_expr
                if not isinstance(call.func, ast.Name):
                    raise SyntaxError("in template scope 'with' may contain only Element() or [element_tag](),"
                                      " '{}' template".format(self.template_name))

                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    del_vars = False
                    element_id = item.optional_vars.id
                else:
                    del_vars = True
                    element_id = "__{}_{}__".format(call.func.id, id(call))
                    _as = ast.Name(id=element_id, ctx=ast.Store())
                    item.optional_vars = _as

                if call.func.id == "Element":
                    body = []
                else:
                    append_call = ast.Call(
                        func=ast.Attribute(value=ast.Name(id=element_name, ctx=ast.Load()),
                                           attr='append', ctx=ast.Load()),
                        args=[ast.Name(id=element_id, ctx=ast.Load())], keywords=[])
                    body = [ast.Expr(value=append_call)]

                for node in with_node.body:
                    method = '_visit_' + node.__class__.__name__
                    visitor = getattr(self, method, None)
                    if visitor is not None:
                        node = visitor(node, element_id)
                    if not isinstance(node, ast.AST):
                        body.extend(node)
                    else:
                        body.append(node)
                if del_vars:
                    body.append(ast.Delete(targets=[ast.Name(id=element_id, ctx=ast.Del())]))
                with_node.body = body

        return with_node

    def _visit_If(self, node, element_name='__template__'):
        return self._visit_stmt_(node, element_name)

    def _visit_For(self, node, element_name='__template__'):
        return self._visit_stmt_(node, element_name)


    def _visit_stmt_(self, stmt_node, element_name='__template__'):
        def _visit(field):
            content = []
            for node in getattr(stmt_node, field):
                method = '_visit_' + node.__class__.__name__
                visitor = getattr(self, method, None)
                if visitor is not None:
                    node = visitor(node, '__wrap_template__')
                if not isinstance(node, ast.AST):
                    content.extend(node)
                else:
                    content.append(node)
            setattr(stmt_node, field, content)

        for field in ["body", "orelse"]:
            if field in stmt_node._fields:
                _visit(field)

        func_node = self._wrap_func([stmt_node])
        expr_node = ast.Expr(value=ast.Call(func=ast.Name(id=element_name, ctx=ast.Load()),
                                           args=[ast.Name(id='__wrap_func__', ctx=ast.Load())], keywords=[]))
        return ast.copy_location(func_node, stmt_node), expr_node

    def _wrap_lambda(self, body):
        node = ast.Lambda(args=ast.arguments(args=[], vararg=None, kwonlyargs=[], kw_defaults=[],
                                             kwarg=None, defaults=[]), body=body)
        return ast.copy_location(node, body)

    def _wrap_func(self, body):
        assign = ast.Assign(targets=[ast.Name(id='__wrap_template__', ctx=ast.Store())],
                            value=ast.Call(func=ast.Name(id='Element', ctx=ast.Load()),
                                           args=[ast.NameConstant(value=None)], keywords=[]))
        _return = ast.Return(value=ast.Name(id='__wrap_template__', ctx=ast.Load()))

        func_body = [assign]
        func_body.extend(body)
        func_body.append(_return)

        return ast.FunctionDef(name='__wrap_func__',
                               args=ast.arguments(args=[], vararg=None, kwonlyargs=[],
                                                  kw_defaults=[], kwarg=None, defaults=[]),
                               decorator_list=[],
                               body=func_body,
                               returns=None)
