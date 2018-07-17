from IPython.core.inputtransformer import CoroutineInputTransformer
from naginpy.inputsplitter import splitter, transformer_manager

class DSL(object):
    def logical_line_transform(self):
        PIPE = '<%<'
        line = ''
        while True:
            line = (yield line)
            # consume leading empty lines
            while not line:
                line = (yield line)

            print('original', line)
            line = line.rstrip()
            if not line.endswith(PIPE):
                continue

            lines = []
            while line.endswith(PIPE):
                lines.append(line)
                line = (yield None)

            lines.append(line)
            body = u'\n'.join(lines)
            line = body

def another_one():
    PIPE = '<%<'
    line = ''
    while True:
        line = (yield line)
        # consume leading empty lines
        while not line:
            line = (yield line)

        print('other one', line)
        line = line.rstrip()
        if not line.endswith(PIPE):
            print('woo?', repr(line))
            continue

        lines = []
        while line.endswith(PIPE):
            lines.append(line)
            line = (yield None)

        lines.append(line)
        body = u'\n'.join(lines)
        print('other one222', body)
        line = body

dsl = DSL()

def add_dsl(dsl):
    splitter.logical_line_transforms = splitter.__logical_line_transforms__ + \
            [CoroutineInputTransformer.wrap(dsl.logical_line_transform)(),
            CoroutineInputTransformer.wrap(another_one)()]
    transformer_manager.logical_line_transforms = transformer_manager.__logical_line_transforms__ + \
            [CoroutineInputTransformer.wrap(dsl.logical_line_transform)()]

add_dsl(dsl)
