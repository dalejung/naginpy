import numpy as np

class ArangeSource(object):
    """
    Will just return an np.arange(key)
    """
    source_key = 'aranger'
    def __init__(self):
        self.cache = {}

    def get(self, key):
        if np.isscalar(key):
            key = tuple([key])
        obj = self.cache.get(key, None)
        if obj is None:
            obj = np.arange(*key)
        self.cache[key] = obj
        return self.cache[key]

