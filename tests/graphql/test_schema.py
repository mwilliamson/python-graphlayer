import graphql
from precisely import all_of, anything, assert_that, equal_to, has_attrs, is_instance, is_mapping

import graphlayer as g
from graphlayer.graphql.schema import to_graphql_type


def test_boolean_is_converted_to_non_null_graphql_boolean():
    assert_that(to_graphql_type(g.Boolean), is_graphql_non_null(is_graphql_boolean))


def test_float_is_converted_to_non_null_graphql_float():
    assert_that(to_graphql_type(g.Float), is_graphql_non_null(is_graphql_float))


def test_int_is_converted_to_non_null_graphql_int():
    assert_that(to_graphql_type(g.Int), is_graphql_non_null(is_graphql_int))


def test_string_is_converted_to_non_null_graphql_string():
    assert_that(to_graphql_type(g.String), is_graphql_non_null(is_graphql_string))


def test_list_type_is_converted_to_non_null_list_type():
    assert_that(to_graphql_type(g.ListType(g.Boolean)), is_graphql_list(is_graphql_non_null(is_graphql_boolean)))


def test_nullable_type_is_converted_to_graphql_type_without_non_null():
    assert_that(to_graphql_type(g.NullableType(g.Boolean)), is_graphql_boolean)


def test_object_type_is_converted_to_non_null_graphql_object_type():
    graph_type = g.ObjectType("Obj", fields=(
        g.field("value", type=g.String),
    ))
    
    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_object_type(
            name="Obj",
            fields=is_mapping({
                "value": is_graphql_field(type=is_graphql_non_null(is_graphql_string)),
            }),
        ),
    ))


def test_recursive_object_type_is_converted_to_non_null_graphql_object_type():
    graph_type = g.ObjectType("Obj", fields=lambda: (
        g.field("self", type=graph_type),
    ))
    
    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_object_type(
            name="Obj",
            fields=is_mapping({
                "self": is_graphql_field(type=is_graphql_non_null(is_graphql_object_type(name="Obj"))),
            }),
        ),
    ))


def test_field_param_is_converted_to_non_null_graphql_arg():
    graph_type = g.ObjectType("Obj", fields=(
        g.field("value", type=g.String, params=(
            g.param("arg", g.Int),
        )),
    ))
    
    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_object_type(
            fields=is_mapping({
                "value": is_graphql_field(args=is_mapping({
                    "arg": is_graphql_argument(type=is_graphql_non_null(is_graphql_int)),
                })),
            }),
        ),
    ))


def test_when_param_has_default_then_param_is_converted_to_nullable_graphql_arg():
    graph_type = g.ObjectType("Obj", fields=(
        g.field("value", type=g.String, params=(
            g.param("arg", g.Int, default=42),
        )),
    ))
    
    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_object_type(
            fields=is_mapping({
                "value": is_graphql_field(args=is_mapping({
                    "arg": is_graphql_argument(type=is_graphql_int),
                })),
            }),
        ),
    ))


def test_input_object_type_is_converted_to_non_null_graphql_input_object_type():
    graph_type = g.InputObjectType("Obj", fields=(
        g.input_field("value", type=g.String),
    ))
    
    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_input_object_type(
            name="Obj",
            fields=is_mapping({
                "value": is_graphql_input_field(type=is_graphql_non_null(is_graphql_string)),
            }),
        ),
    ))
    

is_graphql_boolean = equal_to(graphql.GraphQLBoolean)
is_graphql_float = equal_to(graphql.GraphQLFloat)
is_graphql_int = equal_to(graphql.GraphQLInt)
is_graphql_string = equal_to(graphql.GraphQLString)


def is_graphql_input_field(type):
    return all_of(
        is_instance(graphql.GraphQLInputObjectField),
        has_attrs(type=type),
    )


def is_graphql_input_object_type(name, fields):
    return all_of(
        is_instance(graphql.GraphQLInputObjectType),
        has_attrs(
            name=name,
            fields=fields,
        ),
    )


def is_graphql_list(element_matcher):
    return all_of(
        is_instance(graphql.GraphQLList),
        has_attrs(of_type=element_matcher),
    )


def is_graphql_non_null(element_matcher):
    return all_of(
        is_instance(graphql.GraphQLNonNull),
        has_attrs(of_type=element_matcher),
    )


def is_graphql_object_type(name=None, fields=None):
    if name is None:
        name = anything
    
    if fields is None:
        fields = anything
    
    return all_of(
        is_instance(graphql.GraphQLObjectType),
        has_attrs(
            name=name,
            fields=fields,
        ),
    )


def is_graphql_field(type=None, args=None):
    if type is None:
        type = anything
    
    if args is None:
        args = anything
    
    return all_of(
        is_instance(graphql.GraphQLField),
        has_attrs(type=type, args=args),
    )


def is_graphql_argument(type):
    return all_of(
        is_instance(graphql.GraphQLArgument),
        has_attrs(type=type),
    )

