import abc

class ManifestABC(metaclass=abc.ABCMeta):
    """
    An class that represents a deferrable value and can provide that value.
    """
    @abc.abstractmethod
    def get_object(self):
        pass
