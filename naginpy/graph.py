from collections import OrderedDict
import ast

from asttools import is_load_name, graph_walk

class GatherGrapher:
    def __init__(self, code, **kwargs):
        self.gather_check = kwargs.pop('gather_check', is_load_name)
        self.gather_nodes = {}

        if isinstance(code, str):
            code = ast.parse(code)
        self.code = code

        self.graph = {}
        self.depth = {}
        self._processed = False

    def process(self):
        if self._processed:
            raise Exception('Grapher has already processed code')

        for item in graph_walk(self.code):
            node = item['node']
            line = item['line']
            loc = item['location']
            loc = loc['parent'], loc['field_name'], loc['field_index']
            depth = item['depth']

            if self.gather_check(node):
                self.gather_nodes.setdefault(line, []).append(node)

            self.graph[node] = loc
            self.depth[node] = depth
        self._processed = True

    def parent(self, node):
        return self.graph[node]
