import enum

import graphql
from precisely import all_of, anything, assert_that, contains_exactly, equal_to, has_attrs, is_instance, is_mapping

import graphlayer as g
from graphlayer.graphql.schema import create_graphql_schema


def test_boolean_is_converted_to_non_null_graphql_boolean():
    assert_that(to_graphql_type(g.Boolean), is_graphql_non_null(is_graphql_boolean))


def test_float_is_converted_to_non_null_graphql_float():
    assert_that(to_graphql_type(g.Float), is_graphql_non_null(is_graphql_float))


def test_int_is_converted_to_non_null_graphql_int():
    assert_that(to_graphql_type(g.Int), is_graphql_non_null(is_graphql_int))


def test_string_is_converted_to_non_null_graphql_string():
    assert_that(to_graphql_type(g.String), is_graphql_non_null(is_graphql_string))


def test_enum_is_converted_to_non_null_enum_type():
    class Season(enum.Enum):
        winter = "WINTER"
        spring = "SPRING"
        summer = "SUMMER"
        autumn = "AUTUMN"

    SeasonGraphType = g.EnumType(Season)

    graphql_type = to_graphql_type(SeasonGraphType)

    assert_that(graphql_type, is_graphql_non_null(is_graphql_enum_type(
        name="Season",
        values=contains_exactly(
            is_graphql_enum_value(name="WINTER", value="WINTER"),
            is_graphql_enum_value(name="SPRING", value="SPRING"),
            is_graphql_enum_value(name="SUMMER", value="SUMMER"),
            is_graphql_enum_value(name="AUTUMN", value="AUTUMN"),
        ),
    )))


def test_interface_type_is_converted_to_non_null_graphql_interface_type():
    graph_type = g.InterfaceType("Obj", fields=(
        g.field("value", type=g.String),
    ))

    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_interface_type(
            name="Obj",
            fields=is_mapping({
                "value": is_graphql_field(type=is_graphql_non_null(is_graphql_string)),
            }),
        ),
    ))


def test_list_type_is_converted_to_non_null_list_type():
    assert_that(
        to_graphql_type(g.ListType(g.Boolean)),
        is_graphql_non_null(is_graphql_list(is_graphql_non_null(is_graphql_boolean))),
    )


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


def test_object_type_field_names_are_converted_from_snake_case_to_camel_case():
    graph_type = g.ObjectType("Obj", fields=(
        g.field("field_name", type=g.String),
    ))

    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_object_type(
            fields=is_mapping({
                "fieldName": anything,
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


def test_object_type_interfaces_are_converted_to_graphql_interfaces():
    graph_interface_type = g.InterfaceType("Interface", fields=(
        g.field("value", type=g.String),
    ))

    graph_object_type = g.ObjectType(
        "Obj",
        fields=(
            g.field("value", type=g.String),
        ),
        interfaces=(graph_interface_type, ),
    )

    assert_that(to_graphql_type(graph_object_type), is_graphql_non_null(
        is_graphql_object_type(
            interfaces=contains_exactly(
                is_graphql_interface_type(name="Interface"),
            ),
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


def test_param_names_are_converted_from_snake_case_to_camel_case():
    graph_type = g.ObjectType("Obj", fields=(
        g.field("value", type=g.String, params=(
            g.param("arg_zero", g.Int),
        )),
    ))

    assert_that(to_graphql_type(graph_type), is_graphql_non_null(
        is_graphql_object_type(
            fields=is_mapping({
                "value": is_graphql_field(args=is_mapping({
                    "argZero": is_graphql_argument(),
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

    assert_that(to_graphql_input_type(graph_type), is_graphql_non_null(
        is_graphql_input_object_type(
            name="Obj",
            fields=is_mapping({
                "value": is_graphql_input_field(type=is_graphql_non_null(is_graphql_string)),
            }),
        ),
    ))


def test_input_object_type_field_names_are_converted_from_snake_case_to_camel_case():
    graph_type = g.InputObjectType("Obj", fields=(
        g.input_field("field_name", type=g.String),
    ))

    assert_that(to_graphql_input_type(graph_type), is_graphql_non_null(
        is_graphql_input_object_type(
            fields=is_mapping({
                "fieldName": anything,
            }),
        ),
    ))


def test_when_input_field_has_default_then_input_field_type_is_nullable():
    graph_type = g.InputObjectType("Obj", fields=(
        g.input_field("value", type=g.String, default=""),
    ))

    assert_that(to_graphql_input_type(graph_type), is_graphql_non_null(
        is_graphql_input_object_type(
            name="Obj",
            fields=is_mapping({
                "value": is_graphql_input_field(type=is_graphql_string),
            }),
        ),
    ))


def to_graphql_type(graph_type):
    root_type = g.ObjectType("Root", fields=(
        g.field("value", type=graph_type),
    ))
    graphql_schema = create_graphql_schema(query_type=root_type, mutation_type=None).graphql_schema
    return graphql_schema.get_query_type().fields["value"].type


def to_graphql_input_type(graph_type):
    root_type = g.ObjectType("Root", fields=(
        g.field("value", type=g.String, params=(
            g.param("arg0", type=graph_type),
        )),
    ))
    graphql_schema = create_graphql_schema(query_type=root_type, mutation_type=None).graphql_schema
    return graphql_schema.get_query_type().fields["value"].args["arg0"].type


is_graphql_boolean = equal_to(graphql.GraphQLBoolean)
is_graphql_float = equal_to(graphql.GraphQLFloat)
is_graphql_int = equal_to(graphql.GraphQLInt)
is_graphql_string = equal_to(graphql.GraphQLString)


def is_graphql_enum_type(name, values):
    return all_of(
        is_instance(graphql.GraphQLEnumType),
        has_attrs(name=name, values=values),
    )


def is_graphql_enum_value(name, value):
    return all_of(
        is_instance(graphql.GraphQLEnumValue),
        has_attrs(name=name, value=value),
    )


def is_graphql_input_field(type):
    return all_of(
        is_instance(graphql.GraphQLInputObjectField),
        has_attrs(type=type),
    )


def is_graphql_input_object_type(name=None, fields=None):
    if name is None:
        name = anything
    if fields is None:
        fields = anything

    return all_of(
        is_instance(graphql.GraphQLInputObjectType),
        has_attrs(
            name=name,
            fields=fields,
        ),
    )


def is_graphql_interface_type(name, fields=None):
    if fields is None:
        fields = anything

    return all_of(
        is_instance(graphql.GraphQLInterfaceType),
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


def is_graphql_object_type(name=None, fields=None, interfaces=None):
    if name is None:
        name = anything

    if fields is None:
        fields = anything

    if interfaces is None:
        interfaces = anything

    return all_of(
        is_instance(graphql.GraphQLObjectType),
        has_attrs(
            name=name,
            fields=fields,
            interfaces=interfaces,
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


def is_graphql_argument(type=None):
    if type is None:
        type = anything

    return all_of(
        is_instance(graphql.GraphQLArgument),
        has_attrs(type=type),
    )

