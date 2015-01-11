import abc

class ManifestABC(metaclass=abc.ABCMeta):
    """
    An class that represents a deferrable value and can provide that value.

    This ABC was created because ContextObjects and Manifests have the 
    same behaviors, Manifest just includes an Expression to provide its
    value. 
    """
    @abc.abstractmethod
    def get_object(self):
        pass
