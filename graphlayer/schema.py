from functools import reduce

from . import GraphError, iterables
from .memo import lambdaize, memoize
from .representations import Object


_undefined = object()


class ScalarType(object):
    def __init__(self, name, coerce):
        self.name = name
        self._coerce = coerce

    def __call__(self):
        return ScalarQuery(self)

    def __str__(self):
        return self.name

    def child_types(self):
        return ()

    def coerce(self, value):
        return self._coerce(value)


def _coerce_boolean(value):
    if isinstance(value, bool):
        return value
    else:
        raise _coercion_error(value, Boolean)


Boolean = ScalarType("Boolean", coerce=_coerce_boolean)


def _coerce_float(value):
    if isinstance(value, float):
        return value
    elif isinstance(value, int):
        coerced = float(value)
        if coerced == value:
            return coerced

    raise _coercion_error(value, Float)


Float = ScalarType("Float", coerce=_coerce_float)


def _coerce_int(value):
    if isinstance(value, int):
        return value
    else:
        raise _coercion_error(value, Int)


Int = ScalarType("Int", coerce=_coerce_int)


def _coerce_string(value):
    if isinstance(value, str):
        return value
    else:
        raise _coercion_error(value, String)


String = ScalarType("String", coerce=_coerce_string)


class ScalarQuery(object):
    def __init__(self, type):
        self.type = type

    def for_type(self, target_type):
        if self.type == target_type:
            return self
        else:
            raise _query_coercion_error(self.type, target_type)

    def __add__(self, other):
        if not isinstance(other, ScalarQuery):
            return NotImplemented
        elif self.type != other.type:
            raise TypeError("cannot add queries for different scalar types: {} and {}".format(
                self.type,
                other.type,
            ))
        else:
            return self

    def __str__(self):
        return "ScalarQuery(type={})".format(self.type)


class EnumType(object):
    def __init__(self, enum):
        self.enum = enum

    @property
    def name(self):
        return self.enum.__name__

    def __call__(self):
        return EnumQuery(self)

    def __str__(self):
        return self.name

    def child_types(self):
        return ()

    def coerce(self, value):
        if isinstance(value, self.enum):
            return value
        else:
            raise _coercion_error(value, self)


class EnumQuery(object):
    def __init__(self, type):
        self.type = type

    def for_type(self, target_type):
        if self.type == target_type:
            return self
        else:
            raise _query_coercion_error(self.type, target_type)

    def __add__(self, other):
        if not isinstance(other, EnumQuery):
            return NotImplemented
        elif self.type != other.type:
            raise TypeError("cannot add queries for different enum types: {} and {}".format(
                self.type,
                other.type,
            ))
        else:
            return self

    def __str__(self):
        return "EnumQuery(type={})".format(self.type)


class InputObjectType(object):
    def __init__(self, name, fields):
        self.name = name
        self.fields = Fields(name, fields)
        self.instance_type = memoize(self._create_instance_type)

    def _create_instance_type(self):
        name = self.name

        def __init__(self, values):
            self._values = values
            for key in values:
                setattr(self, key, values[key])

        def __eq__(self, other):
            if isinstance(other, instance_type):
                return self._values == other._values
            else:
                return NotImplemented

        def __ne__(self, other):
            return not (self == other)

        def __repr__(self):
            return "{}({})".format(name, ", ".join(
                "{}={!r}".format(key, value)
                for key, value in self._values.items()
            ))

        instance_type = type(
            self.name,
            (object, ),
            dict(
                __init__=__init__,
                __repr__=__repr__,
                __eq__=__eq__,
                __ne__=__ne__,
            ),
        )

        return instance_type

    def __call__(self, **explicit_field_values):
        def get_field_value(field):
            value = explicit_field_values.pop(field.name, field.default)

            if value is _undefined:
                raise GraphError("{} is missing required field {}".format(self.name, field.name))
            else:
                return value

        field_values = iterables.to_dict(
            (field.name, get_field_value(field))
            for field in self.fields
        )

        if explicit_field_values:
            key = next(iter(explicit_field_values))
            raise GraphError("{} has no field {}".format(self.name, key))

        return self.instance_type()(field_values)

    def __repr__(self):
        return "InputObjectType(name={!r})".format(self.name)

    def child_types(self):
        return tuple(
            field.type
            for field in self.fields
        )

    def coerce(self, value):
        if isinstance(value, self.instance_type()):
            return value
        else:
            raise _coercion_error(value, self.name)


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

    def __call__(self, *field_queries):
        return ObjectQuery.create(self, field_queries=field_queries)

    def query(self, *, field_queries, create_object):
        return ObjectQuery.create(self, field_queries=field_queries, create_object=create_object)

    def __repr__(self):
        return "InterfaceType(name={!r})".format(self.name)

    def __str__(self):
        return self.name

    def child_types(self):
        return _fields_child_types(self.fields)


class ListType(object):
    def __init__(self, element_type):
        self.element_type = element_type

    def __call__(self, *args, **kwargs):
        return ListQuery(self, self.element_type(*args, **kwargs))

    def query(self, *args, **kwargs):
        return ListQuery(self, self.element_type.query(*args, **kwargs))

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

    def __str__(self):
        return "List({})".format(self.element_type)

    def child_types(self):
        return (self.element_type, )

    def coerce(self, value):
        return [
            self.element_type.coerce(element)
            for element in value
        ]


class ListQuery(object):
    def __init__(self, type, element_query):
        self.type = type
        self.element_query = element_query

    def for_type(self, target_type):
        if isinstance(target_type, ListType):
            element_query = self.element_query.for_type(target_type.element_type)
            return ListQuery(type=target_type, element_query=element_query)
        else:
            raise _query_coercion_error(self.type, target_type)

    def __add__(self, other):
        if not isinstance(other, ListQuery):
            return NotImplemented
        elif self.type.element_type != other.type.element_type:
            raise TypeError("cannot add queries for lists with different element types: {} and {}".format(
                self.type.element_type,
                other.type.element_type,
            ))
        else:
            return ListQuery(type=self.type, element_query=self.element_query + other.element_query)

    def __str__(self):
        return _format_call_tree("ListQuery", (
            ("type", self.type),
            ("element_query", self.element_query),
        ))



class NullableType(object):
    def __init__(self, element_type):
        self.element_type = element_type

    def __call__(self, *args, **kwargs):
        return NullableQuery(self, self.element_type(*args, **kwargs))

    def query(self, *args, **kwargs):
        return NullableQuery(self, self.element_type.query(*args, **kwargs))

    def __eq__(self, other):
        if isinstance(other, NullableType):
            return self.element_type == other.element_type
        else:
            return NotImplemented

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.element_type)

    def __str__(self):
        return "Nullable({})".format(self.element_type)

    def __repr__(self):
        return "NullableType(element_type={!r})".format(self.element_type)

    def child_types(self):
        return (self.element_type, )

    def coerce(self, value):
        if value is None:
            return None
        else:
            return self.element_type.coerce(value)


class NullableQuery(object):
    def __init__(self, type, element_query):
        self.type = type
        self.element_query = element_query

    def for_type(self, target_type):
        if isinstance(target_type, NullableType):
            element_query = self.element_query.for_type(target_type.element_type)
            return NullableQuery(type=target_type, element_query=element_query)
        else:
            raise _query_coercion_error(self.type, target_type)

    def __add__(self, other):
        if not isinstance(other, NullableQuery):
            return NotImplemented
        elif self.type.element_type != other.type.element_type:
            raise TypeError("cannot add queries for nullables with different element types: {} and {}".format(
                self.type.element_type,
                other.type.element_type,
            ))
        else:
            return NullableQuery(type=self.type, element_query=self.element_query + other.element_query)

    def __str__(self):
        return _format_call_tree("NullableQuery", (
            ("type", self.type),
            ("element_query", self.element_query),
        ))


class ObjectType(object):
    def __init__(self, name, fields, interfaces=None):
        if interfaces is None:
            interfaces = ()

        self.name = name
        if not callable(fields):
            fields = lambdaize(fields)
        def owned_fields():
            return tuple(
                field.with_owner_type(self)
                for field in fields()
            )
        self.fields = Fields(name, owned_fields)
        # TODO: validation of interfaces, especially default values of arguments
        self._interfaces = memoize(interfaces)

    @property
    def interfaces(self):
        return self._interfaces()

    def __call__(self, *field_queries):
        return ObjectQuery.create(self, field_queries=field_queries)

    def query(self, *, field_queries, create_object):
        return ObjectQuery.create(self, field_queries=field_queries, create_object=create_object)

    def __repr__(self):
        return "ObjectType(name={!r})".format(self.name)

    def __str__(self):
        return self.name

    def child_types(self):
        return _fields_child_types(self.fields) + tuple(self.interfaces)


def _fields_child_types(fields):
    return tuple(
        child_type
        for field in fields
        for child_type in field.child_types()
    )


class Fields(object):
    def __init__(self, type_name, fields):
        self._type_name = type_name
        self._fields = memoize(fields)

    def __iter__(self):
        return iter(self._fields())

    def __getattr__(self, field_name):
        field = self._find_field(field_name)

        if field is None and field_name.endswith("_"):
            field = self._find_field(field_name[:-1])

        if field is None:
            raise GraphError("{} has no field {}".format(self._type_name, field_name))
        else:
            return field

    def _find_field(self, field_name):
        return iterables.find(lambda field: field.name == field_name, self._fields(), default=None)


class ObjectQuery(object):
    @staticmethod
    def create(type, *, field_queries, create_object=None):
        if create_object is None:
            create_object = Object

        return ObjectQuery(type, field_queries=field_queries, create_object=create_object)

    def __init__(self, type, field_queries, *, create_object):
        self.type = type
        # TODO: check field queries are valid
        self.field_queries = tuple(field_queries)
        self.create_object = create_object

    # TODO: handling merging of other query types
    def __add__(self, other):
        if isinstance(other, ObjectQuery):
            assert self.type == other.type

            field_queries = list(map(
                _merge_field_queries,
                iterables.to_multidict(
                    ((field.field, field.key), field)
                    for field in (self.field_queries + other.field_queries)
                ).values(),
            ))

            return ObjectQuery(
                type=self.type,
                field_queries=field_queries,
                create_object=self.create_object,
            )
        else:
            return NotImplemented

    def for_type(self, target_type):
        if self.type == target_type:
            return self

        elif self._is_in_type_hierarchy(target_type):
            field_queries = _field_queries_for_type(self.field_queries, target_type)
            return ObjectQuery(
                type=target_type,
                field_queries=field_queries,
                create_object=self.create_object,
            )

        else:
            raise _query_coercion_error(self.type, target_type)

    def _is_in_type_hierarchy(self, target_type):
        return (
            (
                isinstance(self.type, InterfaceType) and
                isinstance(target_type, ObjectType) and
                self.type in target_type.interfaces
            ) or
            (
                isinstance(self.type, ObjectType) and
                isinstance(target_type, InterfaceType) and
                target_type in self.type.interfaces
            )
        )

    def __str__(self):
        field_queries = _format_tuple(
            str(field_query)
            for field_query in self.field_queries
        )
        return _format_call_tree("ObjectQuery", (
            ("type", self.type.name),
            ("field_queries", field_queries),
        ))


def _field_queries_for_type(field_queries, target_type):
    if isinstance(target_type, InterfaceType):
        return field_queries
    else:
        supertype_fields = frozenset(
            field
            for possible_type in target_type.interfaces
            for field in possible_type.fields
        )

        def field_query_for_type(field_query):
            # TODO: test typename_field outside of GraphQL
            if field_query.field in target_type.fields or field_query.field == typename_field:
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

        return tuple(filter(None, map(field_query_for_type, field_queries)))


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
    return Field(owner_type=None, name=name, type=type, params=params)


class Field(object):
    def __init__(self, owner_type, name, type, params):
        self.owner_type = owner_type
        self.name = name
        self.type = type
        self.params = Params(name, params)

    def with_owner_type(self, owner_type):
        return Field(owner_type=owner_type, name=self.name, type=self.type, params=self.params)

    def __call__(self, *args):
        field_queries, field_args = _partition_by_type(args, (FieldQuery, Argument))
        type_query = self.type(*field_queries)

        # TODO: handle extra args
        return self.query(key=self.name, type_query=type_query, args=field_args)

    def query(self, args, key, type_query):
        explicit_args = iterables.to_dict(
            (arg.parameter.name, arg.value)
            for arg in args
        )

        def get_arg(param):
            value = explicit_args.get(param.name, param.default)

            if value is _undefined:
                raise GraphError("field {} is missing required argument {}".format(self.name, param.name))
            else:
                return value

        field_args = Object(iterables.to_dict(
            (param.name, get_arg(param))
            for param in self.params
        ))

        return FieldQuery(key=key, field=self, type_query=type_query.for_type(self.type), args=field_args)

    def __repr__(self):
        return "Field(name={!r}, type={!r})".format(self.name, self.type)

    def child_types(self):
        return (self.type, ) + tuple(
            param.type
            for param in self.params
        )


def _partition_by_type(values, types):
    results = tuple([] for type in types)

    for value in values:
        potential_results = [
            result
            for type, result in zip(types, results)
            if isinstance(value, type)
        ]
        if potential_results:
            potential_results[0].append(value)
        else:
            raise GraphError("unexpected argument: {!r}\nExpected arguments of type {} but had type {}".format(
                value,
                " or ".join(sorted([type.__name__ for type in types])),
                type(value).__name__,
            ))

    return results


class Params(object):
    def __init__(self, field_name, params):
        self._field_name = field_name
        self._params = params

    def __iter__(self):
        return iter(self._params)

    def __getattr__(self, param_name):
        param = self._find_param(param_name)

        if param is None and param_name.endswith("_"):
            param = self._find_param(param_name[:-1])

        if param is None:
            raise GraphError("{} has no param {}".format(self._field_name, param_name))
        else:
            return param

    def _find_param(self, param_name):
        return iterables.find(lambda param: param.name == param_name, self._params, default=None)


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

    def __str__(self):
        field = "{}.fields.{}".format(self.field.owner_type.name, self.field.name)
        args = _format_tuple(
            "{}.params.{}({})".format(field, param.name, getattr(self.args, param.name))
            for param in self.field.params
        )

        return _format_call_tree("FieldQuery", (
            ("key", '"{}"'.format(self.key)),
            ("field", field),
            ("type_query", self.type_query),
            ("args", args),
        ))


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
        return Argument(parameter=self, value=self.type.coerce(value))


class Argument(object):
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value


def collect_types(types):
    all_types = set()

    def collect(graph_type):
        if graph_type is not None and graph_type not in all_types:
            all_types.add(graph_type)
            for child in graph_type.child_types():
                collect(child)

    for graph_type in types:
        collect(graph_type)

    return all_types


def _format_call_tree(receiver, args):
    return "{}({}\n)".format(receiver, "".join(
        _indent("\n{}={},".format(key, value))
        for key, value in args
    ))


def _format_tuple(elements):
    elements = tuple(elements)
    if elements:
        return "(" + _indent("".join(
            "\n" + element + ","
            for element in elements
        )) + "\n)"
    else:
        return "()"


def _indent(value):
    return value.replace("\n", "\n    ")


def _coercion_error(value, target_type):
    return GraphError("cannot coerce {!r} to {}".format(value, target_type))


def _query_coercion_error(source_type, target_type):
    return TypeError("cannot coerce query for {} to query for {}".format(
        source_type,
        target_type,
    ))


typename_field = field("type_name", type=String)


def to_element_type(graph_type):
    if isinstance(graph_type, (ListType, NullableType)):
        return to_element_type(graph_type.element_type)
    else:
        return graph_type


def replace_element_type(graph_type, element_type):
    if isinstance(graph_type, ListType):
        return ListType(replace_element_type(graph_type.element_type, element_type))
    elif isinstance(graph_type, NullableType):
        return NullableType(replace_element_type(graph_type.element_type, element_type))
    else:
        return element_type
