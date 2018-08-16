from . import iterables


class NoRouteError(Exception):
    pass


def create_graph(expanders):
    return Graph(expanders)

    
class Graph(object):
    def __init__(self, expanders):
        self._expanders_by_type = iterables.to_dict(
            (expander.type, expander)
            for expander in expanders
        )
    
    def expand(self, type, target_representation, context=None):
        if context is None:
            context = {}
        
        expander = self._expanders_by_type[type]
        
        dependencies_for_expander = iterables.to_dict(
            (key, self._get_dependency(expander, context, dependency))
            for key, dependency in expander.dependencies.items()
        )
        
        return expander(self, **dependencies_for_expander)
    
    def _get_dependency(self, expander, context, key):
        if key in context:
            return context[key]
        else:
            raise NoRouteError("Could not find route to {!r} with context {!r}".format(expander.type, context))
        

def expander(type, target_representation, dependencies=None):
    if dependencies is None:
        dependencies = {}
    
    def register_expander(func):
        func.type = type
        func.dependencies = dependencies
        return func
    
    return register_expander

