import ast
from naginpy.asttools import ast_print, ast_source

from ..special_eval import SpecialEval
from ..engine import Engine, NormalEval

sections = []

class DataCacheEngine(Engine):
    def should_handle_line(self, line, load_names):
        return True

    def should_handle_node(self, node, context):
        parent = context.parent
        field = context.field

        handled = True
        if isinstance(parent, ast.Call) and field == 'func':
            handled = True


        print('*'*10)
        ast_print('node:', node)
        ast_print('parent:', parent)
        print('field: ', field)
        print('handled :', handled)

        return handled

    def handle_node(self, node, context):
        if isinstance(node, (ast.BinOp, ast.Call, ast.Subscript, ast.Compare)):
            if node not in sections:
                sections.append(node)
        return node

    def line_postprocess(self, line, ns):
        ast_print(line)

text = """
res = pd.rolling_sum(df.iloc[df.a > df.bob.tail()], 5)
"""
#pd.bob.rolling_sum(df + 1)

class Dale(object):

    def tail(self, var):
        return var

import pandas as pd
import numpy as np
df = pd.DataFrame(np.random.randn(3,3), columns=list('abc'))
dale = Dale()
ns = {}
ns['dale'] = dale
ns['pd'] = pd
ns['df'] = df

se = SpecialEval(text, ns=ns, engines=[DataCacheEngine()])
out = se.process()

print('*'*10)
print('*'*10)
[ast_print(section) for section in sections]
