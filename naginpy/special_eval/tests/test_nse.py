import ast
from naginpy.asttools import ast_print

import pandas as pd
import numpy as np

from ..nse import NSEEngine
from ..special_eval import SpecialEval
from ..engine import NormalEval


text = """
l = dale.tail(dale)
d = dale.tail(df.iloc[:, :])
"""

class Dale(object):

    def tail(self, var):
        return var

dale = Dale()
df = pd.DataFrame(np.random.randn(3,3), columns=list('abc'))

ns = {}
ns['dale'] = dale
ns['df'] = df

se = SpecialEval(text, ns=ns, engines=[NSEEngine(), NormalEval()])
out = se.process()

assert ns['l'] == 'dale'
assert ns['d'] == 'df.iloc[:, :]'
