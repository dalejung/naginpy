import ast
from itertools import zip_longest

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

def field_iter(node):
    """ yield field, field_name, field_index """
    for field_name, field in ast.iter_fields(node):
        if isinstance(field, list):
            for i, item in enumerate(field):
                yield item, field_name, i
            continue

        # need to flatten so we don't have special processing
        # for lists vs single values
        item = field
        yield item, field_name, None


def ast_field_equal(node1, node2):
    """
    Check that fields are equal.

    Note: If the value of the field is an ast.AST and are of equal type,
    we don't check any deeper.
    """
    # check fields
    field_gen1 = field_iter(node1)
    field_gen2 = field_iter(node2)

    for field_item1, field_item2 in zip_longest(field_gen1, field_gen2):
        # unequal length
        if field_item1 is None or field_item2 is None:
            return False

        field_value1 = field_item1[0]
        field_value2 = field_item2[0]

        field_name1 = field_item1[1]
        field_name2 = field_item2[1]

        field_index1 = field_item1[2]
        field_index2 = field_item2[2]

        if type(field_value1) != type(field_value2):
            return False

        if field_name1 != field_name2:
            return False

        if field_index1 != field_index2:
            return False

        # note, we don't do equality check on AST nodes since ast.walk
        # will hit it.
        if isinstance(field_value1, ast.AST):
            continue

        # this should largely be strings and numerics, afaik
        assert isinstance(field_value1, (str, int, float, type(None)))
        if field_value1 != field_value2:
            return False

    return True

def ast_equal(code1, code2, check_line_col=False, ignore_var_names=False):
    """
    Checks whether ast nodes are equivalent recursively.

    By default does not check line number or col offset
    """
    gen1 = ast.walk(code1)
    gen2 = ast.walk(code2)

    for node1, node2 in zip_longest(gen1, gen2):
        # unequal length
        if node1 is None or node2 is None:
            return False

        if type(node1) != type(node2):
            return False

        # ignore the names of load name variables.
        if ignore_var_names and is_load_name(node1) and is_load_name(node2):
            continue

        if not ast_field_equal(node1, node2):
            return False

        if check_line_col and hasattr(node1, 'lineno'):
            if node1.lineno != node2.lineno:
                return False
            if node1.col_offset != node2.col_offset:
                return False

    return True

def ast_contains(code, fragment, ignore_var_names=False):
    """ tests whether fragment is a child within code. """
    expr = _convert_to_expression(fragment)

    if expr is None:
        raise Exception("Fragment must be an expression")

    # unwrap 
    fragment = expr.body

    for node in ast.walk(code):
        if ast_equal(node, fragment, ignore_var_names=ignore_var_names):
            return True

    return False
