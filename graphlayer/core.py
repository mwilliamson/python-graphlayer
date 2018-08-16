from . import iterables


def create_graph(expanders):
    expanders_by_type = iterables.to_dict(
        (expander.type, expander)
        for expander in expanders
    )
    
    class Graph(object):
        def expand(self, type, target_representation, dependencies=None):
            if dependencies is None:
                dependencies = {}
            
            expander = expanders_by_type[type]
            
            dependencies_for_expander = iterables.to_dict(
                (key, dependencies[dependency])
                for key, dependency in expander.dependencies.items()
            )
            
            return expander(self, **dependencies_for_expander)
    
    return Graph()


def expander(type, target_representation, dependencies=None):
    if dependencies is None:
        dependencies = {}
    
    def register_expander(func):
        func.type = type
        func.dependencies = dependencies
        return func
    
    return register_expander

