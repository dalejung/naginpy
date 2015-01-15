import ast
from itertools import zip_longest
from collections import OrderedDict

import pandas as pd
import numpy as np

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

    for item in graph_walk(code):
        node = item['node']
        if ast_equal(node, fragment, ignore_var_names=ignore_var_names):
            return item

    return False

def load_names(code):
    names = (n.id for n in filter(is_load_name, ast.walk(code)))
    return list(OrderedDict.fromkeys(names))

class AstGraphWalker(object):
    """
    Like ast.walk except that it emits a dict:
        {
            node : ast.AST,
            parent : ast.AST,
            field_name : str,
            field_index : int or None,
            current_depth : int
        }

        field_index is None when field is not a list
        current_depth starts from 0 at the top.

    This is largely a copy of AstGrapher but turned into a generator.

    # TODO merge the logic of both visitors.
    """

    def __init__(self, code):
        # 0 based depth
        self.current_depth = -1

        if isinstance(code, str):
            code = ast.parse(code)
        self.code = code
        self._processed = False

    def process(self):
        if self._processed:
            raise Exception('Grapher has already processed code')
        yield from self.visit(self.code)
        self._processed = True

    def visit(self, node):
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        yield from visitor(node)

    def generic_visit(self, node):
        self.current_depth += 1
        for field_name, field in ast.iter_fields(node):
            if isinstance(field, list):
                for i, item in enumerate(field):
                    yield from self.handle_item(node, item, field_name, i)
                continue

            # need to flatten so we don't have special processing
            # for lists vs single values
            item = field
            yield from self.handle_item(node, item, field_name)
        self.current_depth -= 1

    def handle_item(self, parent, node, field_name, i=None):
        """ insert node => (parent, field_name, i) into graph"""
        if not isinstance(node, ast.AST):
            return

        yield {
            'node': node,
            'parent': parent,
            'field_name': field_name,
            'field_index': i,
            'depth': self.current_depth
        }
        yield from self.visit(node) 

def graph_walk(code):
    walker = AstGraphWalker(code)
    return walker.process()

def _value_equal(left, right):
    # TODO move this, make it use dispatch? not sure if there is a general value
    # equality function out there
    if isinstance(left, pd.core.generic.NDFrame):
        return left.equals(right)

    if isinstance(left, np.ndarray):
        return np.all(left == right)

    return left == right

def code_context_subset(code, context, key_code, key_context,
                    ignore_var_names=False):
    """
    Try to find subset match and returns a node context dict as returned
    by ast_contains.

    Returns: dict from ast_contains
        {
            node : ast.AST,
            parent : ast.AST,
            field_name : str,
            field_index : int or None,
            current_depth : int
        }
    """
    # check expresion
    matched_item = ast_contains(code, key_code,
                                    ignore_var_names=ignore_var_names)
    if not matched_item:
        return

    matched_parent = matched_item['node']

    # at this point the load names should be equal for each code
    # fragment. they are equal by position. load_names does not
    # have a set order, but a stable order per same tree structure.
    key_load_names = load_names(key_code)
    matched_load_names = load_names(matched_parent)
    if len(key_load_names) != len(matched_load_names):
        return

    # check context.
    for pk, fk in zip(matched_load_names, key_load_names):
        pv = context[pk]
        fv = key_context[fk]
        if not _value_equal(pv, fv):
            return

    return matched_item
