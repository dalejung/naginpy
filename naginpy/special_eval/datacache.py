import ast
from collections import OrderedDict

from naginpy.asttools import ast_print, ast_source, replace_node, is_load_name

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
        """
        """
        sections = self.sections
        if isinstance(node, (ast.BinOp, ast.Call, ast.Subscript, ast.Compare)):
            if context not in sections:
                sections.append(context)
        return node

    def post_node_loop(self, line, ns):
        sections = self.sections
        dm = self.defer_manager
        # add defer manager to ns. definitely doesn't feel right. revisit

        # start from the smaller bits and move out.
        for context in sorted(sections, key=lambda x: x.depth, reverse=True):
            node = context.node

            # grab the variables referenced by this piece code
            names = set(n.id for n in filter(is_load_name, ast.walk(node)))
            ns_context = {k: ns[k] for k in names}

            entry = dm.get(node, ns_context)

            if not entry.executed:
                dm.execute(entry)

            new_node, ns_update = dm.generate_getter_node(entry)
            replace_node(
                context.parent,
                context.field,
                context.field_index,
                new_node
            )
            ns.update(ns_update)

    def line_postprocess(self, line, ns):
        ast_print(line)
