"""
Taking over IPython

```
def test_any_handle_cell(cell):
    print('any handle', cell)
    return cell

def test_handle_cell(cell):
    print('boo', cell)
    cell += "\nprint('hi')\n"
    return cell

cell_manager = RunCellManager()
cell_manager.patch_run_cell()
cell_manager.add_handler('python_handler', test_handle_cell)
cell_manager.add_handler('any_handler', test_any_handle_cell)
```

"""
import ast

def _patch_run_cell(func):
    ip = get_ipython()
    # save original
    if not hasattr(ip, '__run_cell__'):
        ip.__run_cell__ = ip.run_cell
    ip.run_cell = func.__get__(ip)

class RunCellManager(object):
    def __init__(self):
        self.any_handlers = {}
        self.python_handlers = {}

    def add_handler(self, name, handler, valid_python=True):
        if valid_python:
            handlers = self.python_handlers
        else:
            handlers = self.any_handlers

        handlers[name] = handler

    def handle_cell(self, raw_cell):
        if (not raw_cell) or raw_cell.isspace():
            return raw_cell

        def process_handlers(handlers, raw_cell):
            for name, handler in handlers.items():
                temp = handler(raw_cell)
                # handlers can return None for no-op
                if temp is None:
                    continue
                raw_cell = temp
            return raw_cell

        # going to have to rethink this, won't work for line-oriented
        # clients since they need to parse line to know whether to
        # keep on running.
        # maybe run a two pass? line by line text transform?
        # see core/inputsplitter.py
        raw_cell = process_handlers(self.any_handlers, raw_cell)

        try:
            ast.parse(raw_cell)
        except SyntaxError:
            # not valid python, don't try the python handlers
            return raw_cell

        # note we are assuming that the python handlers are
        # well behaved and return valid python
        raw_cell = process_handlers(self.python_handlers, raw_cell)
        return raw_cell

    def patch_run_cell(self):
        """
        Monkey patch InteractiveShell.run_cell so we can preprocess the
        raw_cell.
        """
        mgr = self
        def run_cell(self, raw_cell, *args, **kwargs):
            raw_cell = mgr.handle_cell(raw_cell)
            return self.__run_cell__(raw_cell, *args, **kwargs)
        _patch_run_cell(run_cell)

def test_any_handle_cell(cell):
    print('2any handle', cell)
    return cell

def test_handle_cell(cell):
    print('boo', cell)
    cell += "\nprint('hi')\n"
    return cell

cell_manager = RunCellManager()
cell_manager.patch_run_cell()
cell_manager.add_handler('python_handler', test_handle_cell)
cell_manager.add_handler('any_handler', test_any_handle_cell)

