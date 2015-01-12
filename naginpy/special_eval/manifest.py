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
import hashlib
import ast

from naginpy.asttools import (ast_source, _eval, is_load_name,
                              _convert_to_expression)
from naginpy.special_eval.manifest_abc import ManifestABC

from .exec_context import (
    ExecutionContext,
)

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
        return hash(self.key)

    _key = None
    @property
    def key(self):
        if self._key is None:
            source_string = self.get_source().encode('utf-8')
            self._key = hashlib.md5(source_string).digest()
        return self._key

    def get_source(self):
        return ast_source(self.code)

    def __eq__(self, other):
        if isinstance(other, Expression):
            return hash(self) == hash(other)
        if isinstance(other, ast.AST):
            return hash(self) == hash(Expression(other))
        if isinstance(other, str):
            return hash(self) == hash(Expression(other))
        # assume bytes is .key
        if isinstance(other, bytes):
            return self.key == other

    def load_names(self):
        # grab the variables referenced by this piece code
        names = set(n.id for n in filter(is_load_name, ast.walk(self.code)))
        return names


class Manifest(object):
    """
    Technically, a manifest can masquerade as the evaluated object since
    we have all we need to create the object.
    """
    def __init__(self, expression, context):

        if not isinstance(expression, Expression):
            raise TypeError("expression must be Expression type")

        if not isinstance(context, ExecutionContext):
            raise TypeError("context must be ExecutionContext type")

        self.expression = expression
        self.context = context

    def __hash__(self):
        return hash(tuple([self.expression, self.context]))

    def __eq__(self, other):
        if isinstance(other, tuple):
            other_expression, other_context = other
        elif isinstance(other, Manifest):
            other_expression = other.expression
            other_context = other.context
        else:
            raise Exception("Can only compare against other manifest or "
                            "tuple(expression, context)")

        # note due to how expression is built, other_expression can be
        # the md5 checksum of the source
        if self.expression != other_expression:
            return False

        if self.context != other_context:
            return False

        return True

    def eval(self):
        return _eval(self.expression.code, self.context.extract())

    def get_obj(self):
        return self.eval()

    @property
    def stateless(self):
        return self.context.stateless

ManifestABC.register(Manifest)

