"""
A Manifest is comprised of:
    1) an Expression, which can be any executable code that takes in inputs.
    2) an execution context, which is normally a dict of ContextObjects

The general idea is for any data to be replicable given a Stateless Manifest.

A Stateless manifest is one where the arguments can be reconstructed i.e. not
directly tied to an object we don't know how to reconstruct.

Something that must be accounted for is nested Manifests, i.e. a Manifest
that has another Stateless Manifest as one of its context varaibles.

As it's very simplest, a Manifest will not be stateless but rely on in-process
ids. While this is less useful than a stateless manifest, it still allows one
to do caching of intermediate entries.

Where the concepts start and end are still up in the air at this point.
"""
import ast

from naginpy.asttools import (ast_source, _eval, is_load_name,
                              _convert_to_expression)

class ContextObject(object):
    """ Represents an input arg to an Expression """
    stateless = False

    def __init__(self, obj):
        self.obj = obj

    def get_obj(self):
        return self.obj

    @property
    def key(self):
        return str(id(self.obj))

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return hash(self) == hash(other)

def get_source_key(source):
    if hasattr(source, 'source_key'):
        return source.source_key
    return id(source)

class SourceObject(ContextObject):
    """
    Simple Stateless object that can take in a dict
    """
    stateless = True

    def __init__(self, source, key, source_key=None):
        self.source = source
        self._obj_key = key
        if source_key is None:
            source_key = get_source_key(source)
        self.source_key = source_key

    def get_obj(self):
        return self.source.get(self._obj_key)

    @property
    def key(self):
        return "{0}::{1}".format(self.source_key, self._obj_key)


class Expression(object):
    """
    For now default to just using ast fragments.
    """
    def __init__(self, code):
        if isinstance(code, str):
            code = ast.parse(code, '<expr>', 'eval')

        # Not sure if i should be converting to ast.Expression here.
        code = _convert_to_expression(code)
        if not code:
            raise Exception("An Expression can only be one logical line."
                            "{0}".format(ast_source(code)))
        self.code = code

    def __hash__(self):
        return hash(self.get_source())

    def get_source(self):
        return ast_source(self.code)

    def __eq__(self, other):
        if isinstance(other, Expression):
            return hash(self) == hash(other)
        if isinstance(other, ast.AST):
            return hash(self) == hash(Expression(other))
        if isinstance(other, str):
            return hash(self) == hash(Expression(other))

    def load_names(self):
        # grab the variables referenced by this piece code
        names = set(n.id for n in filter(is_load_name, ast.walk(self.code)))
        return names


class Manifest(object):
    def __init__(self, expression, context):
        self.expression = expression
        self.context = context

