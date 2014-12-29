import ast
import astdump
import astor

def ast_repr(obj):
    if isinstance(obj, ast.AST):
        return(astor.to_source(obj))
    if isinstance(obj, list):
        return([ast_repr(o) for o in obj])

def ast_print(obj):
    print(ast_repr(obj))

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
