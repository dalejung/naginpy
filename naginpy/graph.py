from collections import OrderedDict
import ast

from asttools import is_load_name

class AstGrapher(object):
    """
    Enhanced visitor that provides parent node mapping and
    keeps track of what Load Varialbes and the line they appear on.


    Note that line refers to the parsed expression/statement found in
    `module.body` and not the source text line.

    self.load_names is keyed by the actual ast.AST. It contains all the
    Name(ctx=Load) found in that line.
    """

    def __init__(self, code):
        self.graph = {}
        self.depth = {}
        # 0 based depth
        self.current_depth = -1

        if isinstance(code, str):
            code = ast.parse(code)
        self.code = code
        self._processed = False

    def process(self):
        if self._processed:
            raise Exception('Grapher has already processed code')
        self.visit(self.code)
        self._processed = True

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        self.current_depth += 1
        for field_name, field in ast.iter_fields(node):
            if isinstance(field, list):
                for i, item in enumerate(field):
                    self.handle_item(node, item, field_name, i)
                continue

            # need to flatten so we don't have special processing
            # for lists vs single values
            item = field
            self.handle_item(node, item, field_name)
        self.current_depth -= 1

    def handle_item(self, parent, node, field_name, i=None):
        """ insert node => (parent, field_name, i) into graph"""
        if not isinstance(node, ast.AST):
            return

        self.graph[node] = ((parent, field_name, i))
        self.depth[node] = self.current_depth
        self.visit(node) 

    def parent(self, node):
        return self.graph[node]

class GatherGrapher(AstGrapher):
    """
    Adds the ability to gather nodes based on a certian condition.
    """

    def __init__(self, *args, **kwargs):
        self.gather_check = kwargs.pop('gather_check', is_load_name)
        self.gather_nodes = {}
        self.line = None

        super().__init__(*args, **kwargs)

    def visit_Module(self, node):
        body = node.body
        for line in node.body:
            self.line = line
            self.generic_visit(line)

    def visit(self, node):
        # check for load name. vars that grab from context
        if self.gather_check(node):
            self.gather_nodes.setdefault(self.line, []).append(node)
        super().visit(node)
