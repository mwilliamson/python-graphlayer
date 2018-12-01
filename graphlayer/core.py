from . import iterables


def create_graph(expanders):
    return Graph(expanders)

    
class Graph(object):
    def __init__(self, expanders):
        self._expanders = iterables.to_dict(
            (expander.type, expander)
            for expander in _flatten(expanders)
        )
    
    def expand(self, query):
        expander = self._expanders[query.type]
        return expander(self, query)


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

