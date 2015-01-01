import ast
import astdump
import astor

def ast_repr(obj):
    if isinstance(obj, ast.AST):
        obj_class = obj.__class__.__name__
        source =  astor.to_source(obj)
        return('ast.{obj_class}: {source}'.format(**locals()))
    if isinstance(obj, list):
        return([ast_repr(o) for o in obj])
    return obj

def ast_print(*objs):
    print(*list(ast_repr(obj) for obj in objs))

def ast_source(obj):
    source =  astor.to_source(obj)
    return source

def replace_node(parent, field, i, new_node):
    if i is None:
        setattr(parent, field, new_node)
    else:
        getattr(parent, field)[i] = new_node

def _eval(node, ns):
    """
    Will eval an ast Node within a namespace.

    If the node is not a statement, it will be evaluated as an
    expression and the result returned.
    """
    expr = node
    mode = 'exec'
    module = ast.Module()
    module.body = [expr]
    if not isinstance(node, ast.stmt):
        module = ast.Expression(lineno=0, col_offset=0, body=node)
        mode = 'eval'
    print('eval', ast_repr(node), mode)
    code = compile(module, '<dale>', mode)
    res = eval(code, ns)
    return res
