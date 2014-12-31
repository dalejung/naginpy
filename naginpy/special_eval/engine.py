from naginpy.asttools import _eval

class Engine(object):
    def should_handle_line(self, line, load_names):
        return False

    def should_handle_node(self, obj, node, parent, field, line):
        pass

    def handle_node(self, obj, node, parent, field, line):
        pass

    def line_postprocess(self, line, ns):
        pass

class NormalEval(Engine):
    def should_handle_line(self, line, load_names):
        return True

    def line_postprocess(self, line, ns):
        res = _eval(line, ns)
        return res
