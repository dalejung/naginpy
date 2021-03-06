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
import binascii
import copy
import hashlib

from asttools import (
    ast_source,
    code_context_subset,
    is_load_name,
    load_names,
    generate_getter_var,
    replace_node,
    _eval,
    _convert_to_expression
)
from naginpy.special_eval.manifest_abc import ManifestABC

from .exec_context import (
    ExecutionContext,
)

def _manifest(code, context):
    """
    So, the Manifest is fairly ornergy about the inputs that it takes in.

    This is a quick and easy Manifest creator
    """
    expression = Expression(code)
    names = expression.load_names()
    # TODO move this logic to Manifest init itself?
    in_expression = lambda x: x[0] in names
    ns_context = dict(filter(in_expression, context.items()))
    context = ExecutionContext.from_ns(ns_context)
    manifest = Manifest(expression, context)
    return manifest

class Expression(object):
    """
    For now default to just using ast fragments.
    """
    def __init__(self, code, mutable=False):
        if isinstance(code, str):
            code = ast.parse(code, '<expr>', 'eval')

        # Not sure if i should be converting to ast.Expression here.
        code = _convert_to_expression(code)
        if not code:
            raise Exception("An Expression can only be one logical line."
                            "{0}".format(ast_source(code)))
        self.code = code
        self.mutable = mutable

    def __hash__(self):
        return hash(self.key)

    _key = None
    @property
    def key(self):
        if self._key is None:
            source_string = self.get_source().encode('utf-8')
            self._key = hashlib.md5(source_string).hexdigest()
        return self._key

    def get_source(self):
        return ast_source(self.code)

    def __eq__(self, other):
        if isinstance(other, Expression):
            return hash(self) == hash(other)
        if isinstance(other, ast.AST):
            return hash(self) == hash(Expression(other))
        # assume str is .key
        if isinstance(other, str):
            return self.key == other

    def load_names(self):
        return load_names(self.code)

    def replace(self, new_node, parent, field_name, field_index):
        if not self.mutable:
            raise Exception("This expression is not mutable")
        self._key = None
        replace_node(parent, field_name, field_index, new_node)

    def copy(self, mutable=False):
        """
        Note that this creates a deep copy of AST
        """
        working_ast = copy.deepcopy(self.code)
        return self.__class__(working_ast, mutable=mutable)

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

    @property
    def key(self):
        expr_key = self.expression.key
        context_key = self.context.key
        return "{0}({1})".format(expr_key, context_key)

    def __hash__(self):
        return hash(tuple([self.expression, self.context]))

    def __eq__(self, other):
        if isinstance(other, tuple):
            other_expression, other_context = other
        elif isinstance(other, Manifest):
            other_expression = other.expression
            other_context = other.context
        else:
            raise Exception("Can only compare against other manifest, "
                            "or tuple(expression, context)")

        # note due to how expression is built, other_expression can be
        # the md5 checksum of the source
        if self.expression != other_expression:
            return False

        if self.context != other_context:
            return False

        return True

    def eval(self):
        return _eval(self.expression.code, self.context.extract())

    def eval_with(self, items, ignore_var_names=False):
        """
        items : dict (Manifest => value)
            Will replace the matching Manifest partial with the evaluated
            value.

        """
        if isinstance(items, list):
            items = dict(zip(items, items))

        working_ast = self.expression.copy(mutable=True)
        working_ns = self.context.copy(mutable=True)

        for manifest, value in items.items():
            matches = code_context_subset(working_ast.code, working_ns,
                                    manifest.expression.code, manifest.context,
                                       ignore_var_names=ignore_var_names)
            matched = False
            for item in matches:
                matched = True
                getter, ns_update = generate_getter_var(manifest, value)

                working_ast.replace(getter, **item['location'])
                working_ns.update(ns_update, wrap=True)

            if not matched:
                raise Exception("{0} was not found".format(manifest.key))

        val = Manifest(working_ast, working_ns).eval()
        return val

    def get_obj(self):
        return self.eval()

    def copy(self, mutable=False):
        working_ast = self.expression.copy(mutable=True)
        working_ns = self.context.copy(mutable=True)
        wm = Manifest(working_ast, working_ns)
        return wm

    def expand(self):
        """
        Takes a Manifest with Manifests in its ExecutionContext
        and substitutes in the sub Manifest.

        Example:

        Manifest1:
            A + B
            {A: 1, B: Manifest2}
        Manifest2:
            C + D
            {C: 2, D: 3}

        Manifest1.expand():
            A + (C + D)
            {A: 1, C:2, D:3}
        """
        wm = self.copy(mutable=True)

        for k, v in self.context.items():
            if not isinstance(v, Manifest):
                continue

            var = ast.parse(k, mode='eval')
            key = _manifest(var, {k: v})
            matches = wm.subset(key)

            # replace with expanded partial. that partial might have its own
            v = v.expand()
            for match in matches:
                new_node = v.expression.code.body
                wm.expression.replace(new_node, **match['location'])
                wm.context.update(v.context)

            if k not in v.context:
                del wm.context[k]

        return wm

    @property
    def stateless(self):
        return self.context.stateless

    def subset(self, key, ignore_var_names=True):
        code = self.expression.code
        context = self.context

        key_code = key.expression.code
        key_context = key.context
        yield from code_context_subset(code, context, key_code, key_context,
                               ignore_var_names=ignore_var_names)

    def __contains__(self, other):
        matched_item = list(self.subset(other, ignore_var_names=True))

        if not matched_item:
            return False

        return True

ManifestABC.register(Manifest)

