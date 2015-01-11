import ast
import astdump
import astor

def ast_repr(obj):
    if isinstance(obj, ast.AST):
        obj_class = obj.__class__.__name__
        source =  ast_source(obj)
        return('ast.{obj_class}: {source}'.format(**locals()))
    if isinstance(obj, list):
        return([ast_repr(o) for o in obj])
    return obj

def ast_print(*objs):
    print(*list(ast_repr(obj) for obj in objs))

def ast_source(obj):
    # astor doens't support ast.Expression atm
    if isinstance(obj, ast.Expression):
        obj = obj.body
    source =  astor.to_source(obj)
    return source

def replace_node(parent, field, i, new_node):
    if i is None:
        setattr(parent, field, new_node)
    else:
        getattr(parent, field)[i] = new_node

def _convert_to_expression(node):
    """ convert ast node to ast.Expression if possible, None if not """
    node = ast.fix_missing_locations(node)

    if isinstance(node, ast.Module):
        if len(node.body) != 1:
            return None
        if isinstance(node.body[0], ast.Expr):
            expr = node.body[0]
            # an expression that was compiled with mode='exec'
            return ast.Expression(lineno=0, col_offset=0, body=expr.value)

    if isinstance(node, ast.Expression):
        return node

    if isinstance(node, ast.expr):
        return ast.Expression(lineno=0, col_offset=0, body=node)

    if isinstance(node, ast.Expr):
        return ast.Expression(lineno=0, col_offset=0, body=node.value)

def _exec(node, ns):
    """
    A kind of catch all exec/eval. It will try to do an eval if possible.

    Fall back to exec
    """
    node = ast.fix_missing_locations(node)

    mode = 'exec'
    if not isinstance(node, ast.Module):
        module = ast.Module()
        module.body = [node]

    # try expression eval
    expr = _convert_to_expression(node)
    if expr:
        module = expr
        mode = 'eval'

    print('eval', ast_repr(node), mode)
    code = compile(module, '<dale>', mode)
    res = eval(code, ns)
    return res

def _eval(node, ns):
    """
    Will eval an ast Node within a namespace.
    """
    expr = _convert_to_expression(node)
    if expr is None:
        raise Exception("{0} cannot be evaled".format(repr(node)))
    return _exec(node, ns)

def is_load_name(node):
    """ is node a Name(ctx=Load()) variable? """
    if not isinstance(node, ast.Name):
        return False

    if isinstance(node.ctx, ast.Load):
        return True
