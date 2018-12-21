from . import iterables
from .representations import ObjectResult


class ScalarType(object):
    def __init__(self, name):
        self.name = name

    def __call__(self):
        return scalar_query


Boolean = ScalarType("Boolean")
Float = ScalarType("Float")
Int = ScalarType("Int")
String = ScalarType("String")


class ScalarQuery(object):
    def to_json_value(self, value):
        return value


scalar_query = ScalarQuery()


class ListType(object):
    def __init__(self, element_type):
        self.element_type = element_type
    
    def __call__(self, *args, **kwargs):
        return ListQuery(self, self.element_type(*args, **kwargs))
    
    def __eq__(self, other):
        if isinstance(other, ListType):
            return self.element_type == other.element_type
        else:
            return NotImplemented
    
    def __ne__(self, other):
        return not (self == other)
    
    def __hash__(self):
        return hash(self.element_type)
    
    def __repr__(self):
        return "ListType(element_type={!r})".format(self.element_type)


class ListQuery(object):
    def __init__(self, type, element_query):
        self.type = type
        self.element_query = element_query

    def to_json_value(self, value):
        return [
            self.element_query.to_json_value(element)
            for element in value
        ]



class NullableType(object):
    def __init__(self, element_type):
        self.element_type = element_type
    
    def __call__(self, *args, **kwargs):
        return NullableQuery(self, self.element_type(*args, **kwargs))
    
    def __eq__(self, other):
        if isinstance(other, NullableType):
            return self.element_type == other.element_type
        else:
            return NotImplemented
    
    def __ne__(self, other):
        return not (self == other)
    
    def __hash__(self):
        return hash(self.element_type)
    
    def __repr__(self):
        return "NullableType(element_type={!r})".format(self.element_type)


class NullableQuery(object):
    def __init__(self, type, element_query):
        self.type = type
        self.element_query = element_query

    def to_json_value(self, value):
        if value is None:
            return None
        else:
            return self.element_query.to_json_value(value)


class ObjectType(object):
    def __init__(self, name, fields):
        self._name = name
        self.fields = Fields(name, fields)
    
    def __call__(self, **fields):
        return ObjectQuery(self, fields)

    def __repr__(self):
        return "ObjectType(name={!r})".format(self._name)


class Fields(object):
    def __init__(self, type_name, fields):
        self._type_name = type_name
        if not callable(fields):
            fields = _lambdaise(fields)
        self._fields = _memoize(fields)
    
    def __getattr__(self, field_name):
        field = iterables.find(lambda field: field.name == field_name, self._fields(), default=None)
        if field is None:
            raise ValueError("{} has no field {}".format(self._type_name, field_name))
        else:
            return field


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

    def to_json_value(self, value):
        return iterables.to_dict(
            (key, self.fields[key].type_query.to_json_value(value))
            for key, value in value._values.items()
        )


class Args(object):
    pass


def field(name, type, params=None):
    return Field(name=name, type=type, params=params)


class Field(object):
    def __init__(self, name, type, params):
        self.name = name
        self.type = type
        self._params = params
    
    def __getattr__(self, param_name):
        return iterables.find(lambda param: param.name == param_name, self._params)
    
    def __call__(self, *args, **kwargs):
        field_args = ObjectResult(iterables.to_dict(
            (arg.parameter.name, arg.value)
            for arg in args
        ))
        return FieldQuery(field=self, type_query=self.type(**kwargs), args=field_args)
    
    def __repr__(self):
        return "Field(name={!r}, type={!r})".format(self.name, self.type)


class FieldQuery(object):
    def __init__(self, field, type_query, args):
        self.field = field
        self.type_query = type_query
        self.args = args


def param(name, type):
    return Parameter(name=name, type=type)


class Parameter(object):
    def __init__(self, name, type):
        self.name = name
        self.type = type
    
    def __call__(self, value):
        return Argument(parameter=self, value=value)


class Argument(object):
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value
