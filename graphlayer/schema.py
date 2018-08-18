from . import iterables


object_query = object()


class IntType(object):
    pass


class StringType(object):
    pass


class ListType(object):
    def __init__(self, element_type):
        self._element_type = element_type
    
    def __call__(self, *args, **kwargs):
        return ListQuery(self, self._element_type(*args, **kwargs))
    
    def __eq__(self, other):
        if isinstance(other, ListType):
            return self._element_type == other._element_type
        else:
            return NotImplemented
    
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
        self._fields = _memoize(fields)
    
    def __getattr__(self, field_name):
        return iterables.find(lambda field: field.name == field_name, self._fields())
    
    def __call__(self, **fields):
        return ObjectQuery(self, fields)
    
    def __repr__(self):
        return "ObjectType(name={!r})".format(self._name)


def _memoize(func):
    result = []
    
    def get():
        if len(result) == 0:
            result.append(func())
        
        return result[0]
    
    return get


def _lambdaise(value):
    return lambda: value


class ObjectQuery(object):
    def __init__(self, type, fields):
        self.type = type
        self.fields = fields


def field(name, type):
    return Field(name=name, type=type)


class Field(object):
    def __init__(self, name, type):
        self.name = name
        self.type = type
    
    def __call__(self, *args, **kwargs):
        return FieldQuery(field=self, type_query=self.type(*args, **kwargs))
    
    def __repr__(self):
        return "Field(name={!r}, type={!r})".format(self.name, self.type)


class FieldQuery(object):
    def __init__(self, field, type_query):
        self.field = field
        self.type_query = type_query
