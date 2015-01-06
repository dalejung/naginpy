import ast
from collections import OrderedDict

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_print, ast_source, replace_node, _eval, is_load_name

from .special_eval import SpecialEval
from .engine import Engine, NormalEval


class DataCacheEngine(Engine):
    def __init__(self, defer_manager):
        self.defer_manager = defer_manager
        self.sections = []

    def should_handle_line(self, line, load_names):
        return True

    def should_handle_node(self, node, context):
        parent = context.parent
        field = context.field

        handled = True
        if isinstance(parent, ast.Call) and field == 'func':
            handled = True

        verbose = False
        if verbose:
            print('*'*10)
            ast_print('node:', node)
            ast_print('parent:', parent)
            print('field: ', field)
            print('handled :', handled)

        return handled

    def handle_node(self, node, context):
        sections = self.sections
        if isinstance(node, (ast.BinOp, ast.Call, ast.Subscript, ast.Compare)):
            if context not in sections:
                sections.append(context)
        return node

    def post_node_loop(self, line, ns):
        sections = self.sections
        dm = self.defer_manager
        ns['defer_manager'] = dm

        for context in sorted(sections, key=lambda x: x.depth, reverse=True):
            node = context.node

            names = set(n.id for n in filter(is_load_name, ast.walk(node)))
            ns_context = {k: ns[k] for k in names}

            entry = dm.get(node, ns_context)

            if not entry.executed:
                with Timer(verbose=False) as t:
                    res = _eval(entry.code, ns)
                entry.value = res
                entry.exec_time = t.interval
                entry.executed = True

            new_node = dm.generate_getter_node(entry)
            replace_node(
                context.parent,
                context.field,
                context.field_index,
                new_node
            )

    def line_postprocess(self, line, ns):
        ast_print(line)
