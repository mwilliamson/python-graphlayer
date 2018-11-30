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


def _flatten(values):
    return [
        value
        for element in values
        for value in (element if isinstance(element, list) else [element])
    ]


def expander(type):
    def register_expander(func):
        func.type = type
        return func
    
    return register_expander

