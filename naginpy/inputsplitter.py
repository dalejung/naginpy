from IPython.core.inputsplitter import IPythonInputSplitter
from functools import partial

ip = get_ipython()

overrides = ['push', 'push_accepts_more', 'physical_line_transforms',
             'logical_line_transforms']

transformer_manager = ip.input_transformer_manager
splitter = ip.input_splitter

def backup(obj, name):
    old_name = '__{0}__'.format(name)
    if hasattr(obj, old_name):
        return
    setattr(obj, old_name, getattr(obj, name))


def backup_attributes(obj, overrides):
    list(map(partial(backup, obj), overrides))

backup_attributes(splitter, overrides)
backup_attributes(transformer_manager, overrides)

# don't think I need these anymore
def _():
    def push(self, line):
        out = self.__push__(line)
        return out

    def push_accepts_more(self):
        out = self.__push_accepts_more__()
        return out

    splitter.push = push.__get__(splitter)
    splitter.push_accepts_more = push_accepts_more.__get__(splitter)
