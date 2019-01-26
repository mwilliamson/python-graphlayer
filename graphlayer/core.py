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
        self._injector = Injector(dependencies)

    def resolve(self, *args, type=None):
        if type is None:
            type = args[0].type
        resolver = self._resolvers.get(type)
        if resolver is None:
            raise GraphError("could not find resolver for query of type: {}".format(type))
        else:
            return self._injector.call_with_dependencies(resolver, self, *args)


class Injector(object):
    def __init__(self, dependencies):
        self._dependencies = dependencies.copy()
        self._dependencies[Injector] = self

    def get(self, key):
        return self._dependencies[key]

    def call_with_dependencies(self, func, *args, **kwargs):
        dependencies = getattr(func, "dependencies", dict())
        dependency_kwargs = iterables.to_dict(
            (arg_name, self.get(dependency_key))
            for arg_name, dependency_key in dependencies.items()
        )
        return func(*args, **kwargs, **dependency_kwargs)


def _flatten(value):
    if isinstance(value, (list, tuple)):
        return [
            subelement
            for element in value
            for subelement in _flatten(element)
        ]
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


class GraphError(Exception):
    pass
