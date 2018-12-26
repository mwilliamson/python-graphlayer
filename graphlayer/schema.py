from functools import reduce

from . import iterables
from .representations import Object


_undefined = object()


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
    
    def __add__(self, other):
        if isinstance(other, ScalarQuery):
            return self
        else:
            return NotImplemented


scalar_query = ScalarQuery()


class EnumType(object):
    def __init__(self, enum):
        self.enum = enum

    @property
    def name(self):
        return self.enum.__name__

    def __call__(self):
        return EnumQuery()


class EnumQuery(object):
    def to_json_value(self, value):
        return value.value


class InputObjectType(object):
    def __init__(self, name, fields):
        self.name = name
        self.fields = Fields(name, fields)
    
    def __call__(self, **explicit_field_values):
        def get_field_value(field):
            value = explicit_field_values.get(field.name, field.default)
            
            if value is _undefined:
                raise ValueError("missing value for {}".format(field.name))
            else:
                return value
        
        field_values = iterables.to_dict(
            (field.name, get_field_value(field))
            for field in self.fields
        )
        # TODO: handle extra field values
        return Object(field_values)

    def __repr__(self):
        return "InputObjectType(name={!r})".format(self.name)


def input_field(name, type, default=_undefined):
    return InputField(name, type, default)


class InputField(object):
    def __init__(self, name, type, default):
        self.name = name
        self.type = type
        self.default = default
    
    @property
    def has_default(self):
        return self.default is not _undefined
    
    def __repr__(self):
        return "InputField(name={!r}, type={!r})".format(self.name, self.type)


class InterfaceType(object):
    def __init__(self, name, fields):
        self.name = name
        self.fields = Fields(name, fields)
        self.subtypes = []

    def __call__(self, *fields):
        return ObjectQuery(self, fields=fields)

    def __repr__(self):
        return "InterfaceType(name={!r})".format(self.name)


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

    def __add__(self, other):
        if isinstance(other, ListQuery):
            # TODO: handle other types
            assert self.type == other.type
            return ListQuery(type=self.type, element_query=self.element_query + other.element_query)
        else:
            return NotImplemented

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
    def __init__(self, name, fields, interfaces=None):
        if interfaces is None:
            interfaces = ()

        self.name = name
        self.fields = Fields(name, fields)
        # TODO: validation of interfaces, especially default values of arguments
        self.interfaces = interfaces

        # TODO: avoiding mutation of the interface would be nicer
        for interface in interfaces:
            interface.subtypes.append(self)
    
    def __call__(self, *fields):
        return ObjectQuery(self, fields=fields)

    def __repr__(self):
        return "ObjectType(name={!r})".format(self.name)


class Fields(object):
    def __init__(self, type_name, fields):
        self._type_name = type_name
        if not callable(fields):
            fields = _lambdaise(fields)
        self._fields = _memoize(fields)
    
    def __iter__(self):
        return iter(self._fields())
    
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
    create_object = Object

    def __init__(self, type, fields):
        self.type = type
        self.fields = tuple(fields)

    # TODO: test this directly
    # TODO: handling merging of other query types
    def __add__(self, other):
        if isinstance(other, ObjectQuery):
            # TODO: better handling of other types
            #~ assert self.type == other.type
            
            fields = list(map(
                _merge_field_queries,
                iterables.to_multidict(
                    ((field.field, field.key), field)
                    for field in (self.fields + other.fields)
                ).values(),
            ))
            
            return ObjectQuery(
                type=self.type,
                fields=fields,
            )
        else:
            return NotImplemented

    def for_type(self, target_type):
        supertype_fields = frozenset(
            field
            for possible_type in target_type.interfaces
            for field in possible_type.fields
        )
        
        def field_query_for_type(field_query):
            if field_query.field in target_type.fields:
                return field_query
            elif field_query.field in supertype_fields:
                field = iterables.find(
                    lambda field: field.name == field_query.field.name,
                    target_type.fields,
                )
                return field_query.for_field(field)
            else:
                # TODO: include subtype fields
                return None
        
        fields = tuple(filter(None, map(field_query_for_type, self.fields)))
        return ObjectQuery(type=target_type, fields=fields)

    def to_json_value(self, value):
        return iterables.to_dict(
            (field_query.key, field_query.type_query.to_json_value(getattr(value, field_query.key)))
            for field_query in self.fields
        )


def _merge_field_queries(fields):
    return reduce(
        lambda left, right: left + right,
        fields,
    )


class Args(object):
    pass


def field(name, type, params=None):
    if params is None:
        params = ()
    return Field(name=name, type=type, params=params)


class Field(object):
    def __init__(self, name, type, params):
        self.name = name
        self.type = type
        self.params = Params(name, params)
    
    def __call__(self, *args, type_query=None):
        # TODO: check for unhandled args

        field_query_args = list(filter(
            lambda arg: isinstance(arg, FieldQuery),
            args,
        ))
        
        if type_query is None:
            type_query = self.type(*field_query_args)
        else:
            # TODO: tidy up the API so this isn't possible
            assert not field_query_args
        
        explicit_args = iterables.to_dict(
            (arg.parameter.name, arg.value)
            for arg in filter(lambda arg: isinstance(arg, Argument), args)
        )
        
        def get_arg(param):
            value = explicit_args.get(param.name, param.default)
            
            if value is _undefined:
                raise ValueError("missing value for {}".format(param.name))
            else:
                return value
        
        field_args = Object(iterables.to_dict(
            (param.name, get_arg(param))
            for param in self.params
        ))
        # TODO: handle extra args
        return FieldQuery(key=self.name, field=self, type_query=type_query, args=field_args)
    
    def __repr__(self):
        return "Field(name={!r}, type={!r})".format(self.name, self.type)


class Params(object):
    def __init__(self, field_name, params):
        self._field_name = field_name
        self._params = params
    
    def __iter__(self):
        return iter(self._params)
    
    def __getattr__(self, param_name):
        param = iterables.find(lambda param: param.name == param_name, self._params, default=None)
        if param is None:
            raise ValueError("{} has no param {}".format(self._field_name, param_name))
        else:
            return param


class FieldQuery(object):
    def __init__(self, key, field, type_query, args):
        self.key = key
        self.field = field
        self.type_query = type_query
        self.args = args
    
    def __add__(self, other):
        if isinstance(other, FieldQuery):
            assert self.key == other.key
            assert self.field == other.field
            assert self.args == other.args
            return FieldQuery(
                key=self.key,
                field=self.field,
                type_query=self.type_query + other.type_query,
                args=self.args,
            )
        else:
            return NotImplemented

    def for_field(self, field):
        # TODO: deal with nullability changes?
        return FieldQuery(
            key=self.key,
            field=field,
            type_query=self.type_query,
            args=self.args,
        )


def key(key, field_query):
    return FieldQuery(
        key=key,
        field=field_query.field,
        type_query=field_query.type_query,
        args=field_query.args,
    )


def param(name, type, default=_undefined):
    return Parameter(name=name, type=type, default=default)


class Parameter(object):
    def __init__(self, name, type, default):
        self.name = name
        self.type = type
        self.default = default
    
    @property
    def has_default(self):
        return self.default is not _undefined
    
    def __call__(self, value):
        return Argument(parameter=self, value=value)


class Argument(object):
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value
