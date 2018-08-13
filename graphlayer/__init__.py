from . import iterables


def executor(expanders):
    expanders_by_type = iterables.to_dict(
        (expander.type, expander)
        for expander in expanders
    )
    
    class Graph(object):
        def expand(self, query, target_representation):
            return expanders_by_type[query.type](self, query)
    
    return lambda query: Graph().expand(query, object_representation)


def expander(type, target_representation):
    def register_expander(func):
        func.type = type
        return func
    
    return register_expander


class Int(object):
    pass


class String(object):
    pass


class List(object):
    def __init__(self, element_type):
        self._element_type = element_type
    
    def __call__(self, *args, **kwargs):
        return ListQuery(self, self._element_type(*args, **kwargs))
    
    def __eq__(self, other):
        if isinstance(other, List):
            return self._element_type == other._element_type
        else:
            raise NotImplemented()
    
    def __ne__(self, other):
        return not (self == other)
    
    def __hash__(self):
        return hash(self._element_type)
    
    def __repr__(self):
        return "List(element_type={!r})".format(self._element_type)


class ListQuery(object):
    def __init__(self, type, element_query):
        self.type = type
        self.element_query = element_query


class ObjectType(object):
    def __init__(self, name, fields):
        self._name = name
        if not callable(fields):
            fields = _lambdaise(fields)
        self._fields = fields
    
    def __getattr__(self, field_name):
        # TODO: memoisation
        return iterables.find(lambda field: field.name == field_name, self._fields())
    
    def __call__(self, **fields):
        return ObjectQuery(self, fields)
    
    def __repr__(self):
        return "List(name={!r})".format(self._name)


def _lambdaise(value):
    return lambda: value


class ObjectQuery(object):
    def __init__(self, type, fields):
        self.type = type
        self.fields = fields


class ObjectResult(object):
    def __init__(self, values):
        for key in values:
            setattr(self, key, values[key])


def field(name, type):
    return Field(name=name, type=type)


class Field(object):
    def __init__(self, name, type):
        self.name = name
        self.type = type
    
    def __call__(self, *args, **kwargs):
        return FieldQuery(field=self, query=self.type(*args, **kwargs))


class FieldQuery(object):
    def __init__(self, field, query):
        self.field = field
        self.query = query


def constant_object_expander(type, values):
    @expander(type, ObjectResult)
    def expand(graph, query):
        return ObjectResult(iterables.to_dict(
            (key, values[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    return expand


object_representation = object()
