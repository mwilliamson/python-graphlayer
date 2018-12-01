from . import iterables


def create_graph(expanders):
    return Graph(expanders)

    
class Graph(object):
    def __init__(self, expanders):
        self._expanders = iterables.to_dict(
            (expander.type, expander)
            for expander in _flatten(expanders)
        )
    
    def expand(self, *args, **kwargs):
        type = kwargs.pop("type", None)
        if type is None:
            type = args[0].type
        # TODO: better error
        assert not kwargs
        expander = self._expanders[type]
        return expander(self, *args)


def _flatten(value):
    if isinstance(value, list):
        return [
            subelement
            for element in value
            for subelement in _flatten(element)
        ]
    elif hasattr(value, "expanders"):
        return _flatten(value.expanders)
    else:
        return [value]


def expander(type):
    def register_expander(func):
        func.type = type
        return func
    
    return register_expander

