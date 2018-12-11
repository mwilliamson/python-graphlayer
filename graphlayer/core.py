from . import iterables


def create_graph(resolvers):
    return define_graph(resolvers).create_graph({})


def define_graph(resolvers):
    return GraphDefinition(resolvers)

    
class GraphDefinition(object):
    def __init__(self, resolvers):
        self._resolvers = iterables.to_dict(
            (resolver.type, resolver)
            for resolver in _flatten(resolvers)
        )
    
    def create_graph(self, dependencies):
        return Graph(self._resolvers, dependencies)


class Graph(object):
    def __init__(self, resolvers, dependencies):
        self._resolvers = resolvers
        self._dependencies = dependencies
    
    def resolve(self, *args, **kwargs):
        type = kwargs.pop("type", None)
        if type is None:
            type = args[0].type
        # TODO: better error
        assert not kwargs
        resolver = self._resolvers[type]
        dependencies = getattr(resolver, "dependencies", dict())
        kwargs = iterables.to_dict(
            (arg_name, self._dependencies[dependency_key])
            for arg_name, dependency_key in dependencies.items()
        )
        return resolver(self, *args, **kwargs)


def _flatten(value):
    if isinstance(value, list):
        return [
            subelement
            for element in value
            for subelement in _flatten(element)
        ]
    elif hasattr(value, "resolvers"):
        return _flatten(value.resolvers)
    else:
        return [value]


def resolver(type):
    def register_resolver(func):
        func.type = type
        return func
    
    return register_resolver


def dependencies(**kwargs):
    def register_dependency(func):
        func.dependencies = kwargs
        return func
    
    return register_dependency
