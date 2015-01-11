from naginpy.asttools import _eval, _exec

class Engine(object):
    """
    should_handle_line : Bool
        Whether engine should handle line. If False, `line_postprocess` 
        will still fire.
    should_handle_node : Bool
        Whether engine should handle individual nodes.
    handle_node : None, ast.AST
        Process node. Return value will replace the current working node.
    post_node_loop : None
        Fires after engine has finished `handle_node` for a single line.
    line_postprocess
        Fire after all lines have been processed by all engines. This is
        more for clean up. It was created primarily for NormalEval
    """
    _allow_missing = False

    def should_handle_line(self, line, load_names):
        return False

    def should_handle_node(self, node, context):
        pass

    def handle_node(self, node, context):
        pass

    def post_node_loop(self, line, ns):
        pass

    def line_postprocess(self, line, ns):
        pass

class NormalEval(Engine):
    def should_handle_line(self, line, load_names):
        return True

    def line_postprocess(self, line, ns):
        res = _exec(line, ns)
        return res
