from collections import OrderedDict
import ast

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

        if isinstance(code, str):
            code = ast.parse(code)
        self.code = code

    def process(self):
        self.visit(self.code)

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        for field_name, field in ast.iter_fields(node):
            if isinstance(field, list):
                for i, item in enumerate(field):
                    self.handle_item(node, item, field_name, i)
                continue

            # need to flatten so we don't have special processing
            # for lists vs single values
            item = field
            self.handle_item(node, item, field_name)

    def handle_item(self, parent, node, field_name, i=None):
        """ insert node => (parent, field_name, i) into graph"""
        if not isinstance(node, ast.AST):
            return

        self.graph[node] = ((parent, field_name, i))
        self.visit(node) 

    def parent(self, node):
        return self.graph[node]

def is_load_name(node):
    if not isinstance(node, ast.Name):
        return False

    if isinstance(node.ctx, ast.Load):
        return True

class TriggerGrapher(AstGrapher):
    def __init__(self, *args, **kwargs):
        self.trigger_check = kwargs.pop('trigger_check', is_load_name)
        self.trigger_nodes = {}
        self.line = None

        super().__init__(*args, **kwargs)

    def visit_Module(self, node):
        body = node.body
        for line in node.body:
            self.line = line
            self.generic_visit(line)

    def visit(self, node):
        # check for load name. vars that grab from context
        if self.trigger_check(node):
            self.trigger_nodes.setdefault(self.line, []).append(node)
        super().visit(node)


