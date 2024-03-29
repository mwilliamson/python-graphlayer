import enum

from precisely import assert_that, equal_to, has_attrs, is_sequence
import pytest

from graphql import GraphQLError
import graphlayer as g
from graphlayer import schema
from graphlayer.graphql.parser import document_text_to_query
from graphlayer.graphql.schema import create_graphql_schema
from ..matchers import is_query


def test_simple_query_is_converted_to_object_query():
    Root = g.ObjectType(
        "Root",
        (
            g.field("one", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            one
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one()),
        ),
    ))


def test_simple_mutation_is_converted_to_object_query():
    QueryRoot = g.ObjectType(
        "Query",
        (
            g.field("query_value", type=g.Int),
        ),
    )
    MutationRoot = g.ObjectType(
        "Mutation",
        (
            g.field("mutation_value", type=g.Int),
        ),
    )

    graphql_query = """
        mutation {
            mutationValue
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=QueryRoot, mutation_type=MutationRoot)

    assert_that(object_query, is_query(
        MutationRoot(
            g.key("mutationValue", MutationRoot.fields.mutation_value()),
        ),
    ))


def test_given_no_mutation_type_is_defined_when_operation_is_mutation_then_error_is_raised():
    QueryRoot = g.ObjectType(
        "Query",
        (
            g.field("query_value", type=g.Int),
        ),
    )

    graphql_query = """
        mutation {
            queryValue
        }
    """

    error = pytest.raises(
        GraphQLError,
        lambda: _document_text_to_graph_query(graphql_query, query_type=QueryRoot),
    )

    assert_that(error.value.message, equal_to("unsupported operation: mutation"))
    assert_that(error.value.nodes, is_sequence(has_attrs(operation=has_attrs(value="mutation"))))


def test_fields_can_have_alias():
    Root = g.ObjectType(
        "Root",
        (
            g.field("one", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            value: one
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("value", Root.fields.one()),
        ),
    ))


def test_field_names_are_converted_to_snake_case():
    Root = g.ObjectType(
        "Root",
        (
            g.field("one_value", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            oneValue
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("oneValue", Root.fields.one_value()),
        ),
    ))


def test_fields_can_be_nested():
    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("one", type=One),
        ),
    )

    One = g.ObjectType(
        "One",
        fields=lambda: (
            g.field("two", type=Two),
        ),
    )

    Two = g.ObjectType(
        "Two",
        fields=lambda: (
            g.field("three", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            one {
                two {
                    three
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one(
                g.key("two", One.fields.two(
                    g.key("three", Two.fields.three()),
                )),
            )),
        ),
    ))


def test_can_request_fields_of_list():
    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("one", type=g.ListType(One)),
        ),
    )

    One = g.ObjectType(
        "One",
        fields=lambda: (
            g.field("two", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            one {
                two
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one(
                g.key("two", One.fields.two()),
            )),
        ),
    ))


def test_inline_fragments_are_expanded():
    Root = g.ObjectType(
        "Root",
        (
            g.field("value", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            one: value
            ... on Root {
                two: value
            }
            three: value
            ... on Root {
                four: value
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.value()),
            g.key("two", Root.fields.value()),
            g.key("three", Root.fields.value()),
            g.key("four", Root.fields.value()),
        ),
    ))


def test_named_fragments_are_expanded():
    Root = g.ObjectType(
        "Root",
        (
            g.field("value", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            one: value
            ...Two
            three: value
            ...Four
        }

        fragment Two on Root {
            two: value
        }

        fragment Four on Root {
            four: value
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.value()),
            g.key("two", Root.fields.value()),
            g.key("three", Root.fields.value()),
            g.key("four", Root.fields.value()),
        ),
    ))


# TODO: handle fragments for different types with same field name
def test_fragments_can_be_on_more_specific_type():
    Animal = g.InterfaceType(
        "Animal",
        fields=(
            g.field("name", type=g.String),
        ),
    )

    Cat = g.ObjectType(
        "Cat",
        fields=(
            g.field("name", type=g.String),
            g.field("whisker_count", type=g.Int),
        ),
        interfaces=(Animal, ),
    )

    Root = g.ObjectType(
        "Root",
        (
            g.field("animal", type=Animal),
        ),
    )

    graphql_query = """
        query {
            animal {
                name
                ... on Cat {
                    whiskerCount
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root, types=(Cat, ))

    assert_that(object_query, is_query(
        Root(
            g.key("animal", Root.fields.animal(
                g.key("name", Animal.fields.name()),
                g.key("whiskerCount", Cat.fields.whisker_count()),
            )),
        ),
    ))


def test_when_fragments_have_common_fields_then_fragments_are_merged():
    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("user", type=User),
        ),
    )

    User = g.ObjectType(
        "User",
        fields=(
            g.field("name", type=g.String),
            g.field("address", type=g.String),
        ),
    )

    graphql_query = """
        query {
            ... on Root {
                user {
                    name
                }
            }
            ... on Root {
                user {
                    address
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("user", Root.fields.user(
                g.key("name", User.fields.name()),
                g.key("address", User.fields.address()),
            )),
        ),
    ))


def test_when_merging_fragments_then_scalar_fields_can_overlap():
    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("user", type=User),
        ),
    )

    User = g.ObjectType(
        "User",
        fields=(
            g.field("name", type=g.String),
            g.field("address", type=g.String),
            g.field("role", type=g.String),
        ),
    )

    graphql_query = """
        query {
            ... on Root {
                user {
                    name
                    address
                }
            }
            ... on Root {
                user {
                    name
                    role
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("user", Root.fields.user(
                g.key("name", User.fields.name()),
                g.key("address", User.fields.address()),
                g.key("role", User.fields.role()),
            )),
        ),
    ))


def test_when_merging_fragments_then_nested_object_fields_can_overlap():
    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("user", type=User),
        ),
    )

    User = g.ObjectType(
        "User",
        fields=lambda: (
            g.field("address", type=Address),
        ),
    )

    Address = g.ObjectType(
        "Address",
        fields=lambda: (
            g.field("first_line", type=g.String),
            g.field("city", type=g.String),
            g.field("postcode", type=g.String),
        ),
    )

    graphql_query = """
        query {
            ... on Root {
                user {
                    address {
                        firstLine
                        city
                    }
                }
            }
            ... on Root {
                user {
                    address {
                        city
                        postcode
                    }
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("user", Root.fields.user(
                g.key("address", User.fields.address(
                    g.key("firstLine", Address.fields.first_line()),
                    g.key("city", Address.fields.city()),
                    g.key("postcode", Address.fields.postcode()),
                )),
            )),
        ),
    ))


def test_fragments_are_recursively_merged():
    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("value", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            ... on Root {
                ... on Root {
                    one: value
                }
            }
            ... on Root {
                ... on Root {
                    two: value
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.value()),
            g.key("two", Root.fields.value()),
        ),
    ))


def test_fragment_can_be_spread_into_list_type():
    User = g.ObjectType("User", fields=lambda: (
        g.field("name", type=g.String),
    ))

    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("user", type=g.ListType(User)),
        ),
    )

    graphql_query = """
        query {
            user {
                ... on User {
                    name
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("user", Root.fields.user(
                g.key("name", User.fields.name()),
            )),
        ),
    ))


def test_fragment_can_be_spread_into_nullable_type():
    User = g.ObjectType("User", fields=lambda: (
        g.field("name", type=g.String),
    ))

    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("user", type=g.NullableType(User)),
        ),
    )

    graphql_query = """
        query {
            user {
                ... on User {
                    name
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("user", Root.fields.user(
                g.key("name", User.fields.name()),
            )),
        ),
    ))


def test_fragment_fields_are_updated_to_fields_for_element_type():
    Person = g.InterfaceType(
        "Person",
        fields=lambda: (
            g.field("name", type=g.String),
        ),
    )

    User = g.ObjectType(
        "User",
        fields=lambda: (
            g.field("name", type=g.String),
        ),
        interfaces=lambda: (Person, ),
    )

    Root = g.ObjectType(
        "Root",
        fields=lambda: (
            g.field("users", type=g.ListType(g.NullableType(User))),
        ),
    )

    graphql_query = """
        query {
            users {
                ... on Person {
                    name
                }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("users", Root.fields.users(
                g.key("name", User.fields.name()),
            )),
        ),
    ))


def test_graphql_field_args_are_read():
    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg0", type=g.String),
                g.param("arg1", type=g.String),
            ]),
        ),
    )

    graphql_query = """
        query {
            one(arg0: "one", arg1: "two")
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one(
                Root.fields.one.params.arg0("one"),
                Root.fields.one.params.arg1("two"),
            )),
        ),
    ))


def test_graphql_field_args_are_converted_to_snake_case():
    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg_zero", type=g.String),
            ]),
        ),
    )

    graphql_query = """
        query {
            one(argZero: "one")
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one(
                Root.fields.one.params.arg_zero("one"),
            )),
        ),
    ))


class Season(enum.Enum):
    winter = "WINTER"
    spring = "SPRING"
    summer = "SUMMER"
    autumn = "AUTUMN"


# TODO: deduplicate arg/variable tests
@pytest.mark.parametrize("arg_type, arg_string, arg_value", [
    (g.Boolean, "true", True),
    (g.Float, "4.2", 4.2),
    (g.Int, "42", 42),
    (g.String, '"value"', "value"),
    (g.EnumType(Season), 'WINTER', Season.winter),
    (g.NullableType(g.Int), "42", 42),
    (g.NullableType(g.Int), "null", None),
    (g.ListType(g.Int), "[]", []),
    (g.ListType(g.Int), "[1, 2, 3]", [1, 2, 3]),
    (
        g.InputObjectType("User", fields=(
            g.input_field("id", type=g.Int),
            g.input_field("name", type=g.String),
        )),
        '{id: 42, name: "Bob"}',
        lambda input_type: input_type(id=42, name="Bob"),
    ),
    (
        g.InputObjectType("Casing", fields=(
            g.input_field("field_zero", type=g.Int),
        )),
        '{fieldZero: 1}',
        lambda input_type: input_type(field_zero=1),
    ),
])
def test_literal_graphql_arg_values_are_converted(arg_type, arg_string, arg_value):
    if callable(arg_value):
        arg_value = arg_value(arg_type)

    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=arg_type),
            ]),
        ),
    )

    graphql_query = """
        query {
            one(arg: %s)
        }
    """ % (arg_string, )

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one(
                Root.fields.one.params.arg(arg_value),
            )),
        ),
    ))


# TODO: deduplicate arg/variable tests
@pytest.mark.parametrize("graph_type, graphql_type, variable_value, arg_value", [
    (g.Boolean, "Boolean!", True, True),
    (g.Float, "Float!", 4.2, 4.2),
    (g.Int, "Int!", 42, 42),
    (g.String, "String!", "value", "value"),
    (g.EnumType(Season), "Season!", "WINTER", Season.winter),
    (g.NullableType(g.Int), "Int", 42, 42),
    (g.NullableType(g.Int), "Int", None, None),
    (g.ListType(g.Int), "[Int!]!", [], []),
    (g.ListType(g.EnumType(Season)), "[Season!]!", ["WINTER"], [Season.winter]),
    (
        g.InputObjectType("User", fields=(
            g.input_field("id", type=g.Int),
            g.input_field("name", type=g.String),
        )),
        "User!",
        {"id": 42, "name": "Bob"},
        lambda input_type: input_type(id=42, name="Bob"),
    ),
    (
        g.InputObjectType("Casing", fields=(
            g.input_field("field_zero", type=g.Int),
        )),
        "Casing!",
        {"fieldZero": 1},
        lambda input_type: input_type(field_zero=1),
    ),
    (
        g.NullableType(g.InputObjectType("User", fields=(
            g.input_field("id", type=g.Int),
            g.input_field("name", type=g.String),
        ))),
        "User",
        {"id": 42, "name": "Bob"},
        lambda input_type: input_type.element_type(id=42, name="Bob"),
    ),
    (
        g.NullableType(g.InputObjectType("User", fields=(
            g.input_field("id", type=g.Int),
            g.input_field("name", type=g.String),
        ))),
        "User",
        None,
        None,
    ),
])
def test_graphql_arg_values_from_variables_are_converted(graph_type, graphql_type, variable_value, arg_value):
    if callable(arg_value):
        arg_value = arg_value(graph_type)

    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=graph_type),
            ]),
        ),
    )

    graphql_query = """
        query ($var: %s) {
            one(arg: $var)
        }
    """ % (graphql_type, )

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root, variables={"var": variable_value})

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one(
                Root.fields.one.params.arg(arg_value),
            )),
        ),
    ))


def test_when_null_variable_is_missing_then_variable_is_null():
    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=g.NullableType(g.Int)),
            ]),
        ),
    )

    graphql_query = """
        query ($var: Int) {
            one(arg: $var)
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root, variables={})

    assert_that(object_query, is_query(
        Root(
            g.key("one", Root.fields.one(
                Root.fields.one.params.arg(None),
            )),
        ),
    ))


def test_when_non_null_variable_is_missing_then_error_is_raised():
    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=g.Int),
            ]),
        ),
    )

    graphql_query = """
        query ($var: Int!) {
            one(arg: $var)
        }
    """

    error = pytest.raises(
        GraphQLError,
        lambda: _document_text_to_graph_query(graphql_query, query_type=Root, variables={}),
    )
    assert_that(error.value.message, equal_to("Variable '$var' of required type 'Int!' was not provided."))


def test_when_input_object_variable_is_missing_field_then_error_is_raised():
    Input = g.InputObjectType(
        "Input",
        fields=lambda: (
            g.input_field("field", type=g.Int),
        ),
    )

    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=Input),
            ]),
        ),
    )

    graphql_query = """
        query ($var: Input!) {
            one(arg: $var)
        }
    """

    variables = {"var": {}}
    error = pytest.raises(
        GraphQLError,
        lambda: _document_text_to_graph_query(graphql_query, query_type=Root, variables=variables),
    )
    assert_that(error.value.message, equal_to("Variable '$var' got invalid value {}; Field 'field' of required type 'Int!' was not provided."))


def test_when_arg_is_not_set_then_default_is_used():
    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg0", type=g.Int, default=None),
                g.param("arg1", type=g.Int, default=42),
            ]),
        ),
    )

    graphql_query = """
        query {
            one
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)
    assert_that(object_query.field_queries[0].args, has_attrs(
        arg0=None,
        arg1=42,
    ))


def test_when_field_value_is_not_set_then_default_is_used():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int, default=None),
            schema.input_field("field1", type=schema.Int, default=42),
        ),
    )

    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=Input),
            ]),
        ),
    )

    graphql_query = """
        query {
            one(arg: {})
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)
    assert_that(object_query.field_queries[0].args.arg, has_attrs(
        field0=None,
        field1=42,
    ))


def test_when_field_value_in_nullable_input_object_is_not_set_then_default_is_used():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int, default=42),
        ),
    )

    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=g.NullableType(Input)),
            ]),
        ),
    )

    graphql_query = """
        query {
            one(arg: {})
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)
    assert_that(object_query.field_queries[0].args.arg, has_attrs(
        field0=42,
    ))


def test_when_field_value_in_input_object_in_list_is_not_set_then_default_is_used():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int, default=42),
        ),
    )

    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=g.ListType(Input)),
            ]),
        ),
    )

    graphql_query = """
        query {
            one(arg: [{}])
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)
    assert_that(object_query.field_queries[0].args.arg, is_sequence(
        has_attrs(
            field0=42,
        ),
    ))


def test_when_field_value_in_input_object_in_input_object_is_not_set_then_default_is_used():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int, default=42),
        ),
    )
    OuterInput = schema.InputObjectType(
        "OuterInput",
        fields=(
            schema.input_field("value", type=Input),
        ),
    )

    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int, params=[
                g.param("arg", type=OuterInput),
            ]),
        ),
    )

    graphql_query = """
        query {
            one(arg: {value: {}})
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)
    assert_that(object_query.field_queries[0].args.arg, has_attrs(
        value=has_attrs(
            field0=42,
        ),
    ))


def test_when_only_schema_is_read_then_graph_query_is_none():
    Root = g.ObjectType(
        "Root",
        fields=(
            g.field("one", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            __schema {
                queryType { name }
            }
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, equal_to(None))


def test_query_is_validated():
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))

    graphql_query = """
        {
            x
        }
    """

    error = pytest.raises(GraphQLError, lambda: _document_text_to_graph_query(graphql_query, query_type=Root))
    assert_that(error.value.message, equal_to("Cannot query field 'x' on type 'Root'."))


def test_when_field_has_camel_case_name_then_field_can_be_referenced_in_query():
    Root = g.ObjectType(
        "Root",
        (
            g.field("camelCase", type=g.Int),
        ),
    )

    graphql_query = """
        query {
            camelCase
        }
    """

    object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

    assert_that(object_query, is_query(
        Root(
            g.key("camelCase", Root.fields.camelCase()),
        ),
    ))


class TestDirectives(object):
    def test_when_include_directive_is_true_then_selection_is_included(self):
        Root = g.ObjectType(
            "Root",
            (
                g.field("one", type=g.Int),
            ),
        )

        graphql_query = """
            query {
                includedField: one @include(if: true)
                excludedField: one @include(if: false)
            }
        """

        object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

        assert_that(object_query, is_query(
            Root(
                g.key("includedField", Root.fields.one()),
            ),
        ))

    def test_when_skip_directive_is_true_then_selection_is_excluded(self):
        Root = g.ObjectType(
            "Root",
            (
                g.field("one", type=g.Int),
            ),
        )

        graphql_query = """
            query {
                includedField: one @skip(if: false)
                excludedField: one @skip(if: true)
            }
        """

        object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

        assert_that(object_query, is_query(
            Root(
                g.key("includedField", Root.fields.one()),
            ),
        ))

    def test_directives_can_be_used_on_inline_fragments(self):
        Root = g.ObjectType(
            "Root",
            (
                g.field("one", type=g.Int),
            ),
        )

        graphql_query = """
            query {
                ... on Root @include(if: true) {
                    includedField: one
                }
                ... on Root @include(if: false) {
                    excludedField: one
                }
            }
        """

        object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

        assert_that(object_query, is_query(
            Root(
                g.key("includedField", Root.fields.one()),
            ),
        ))

    def test_directives_can_be_used_on_fragment_spreads(self):
        Root = g.ObjectType(
            "Root",
            (
                g.field("one", type=g.Int),
            ),
        )

        graphql_query = """
            query {
                ... IncludedFragment @include(if: true)
                ... ExcludedFragment @include(if: false)
            }

            fragment IncludedFragment on Root {
                includedField: one
            }

            fragment ExcludedFragment on Root {
                excludedField: one
            }
        """

        object_query = _document_text_to_graph_query(graphql_query, query_type=Root)

        assert_that(object_query, is_query(
            Root(
                g.key("includedField", Root.fields.one()),
            ),
        ))

    def test_directives_can_use_variables(self):
        Root = g.ObjectType(
            "Root",
            (
                g.field("one", type=g.Int),
            ),
        )

        graphql_query = """
            query ($t: Boolean!, $f: Boolean!) {
                includedField: one @include(if: $t)
                excludedField: one @include(if: $f)
            }
        """

        object_query = _document_text_to_graph_query(
            graphql_query,
            query_type=Root,
            variables={"t": True, "f": False},
        )

        assert_that(object_query, is_query(
            Root(
                g.key("includedField", Root.fields.one()),
            ),
        ))

    def test_when_directive_is_unrecognised_then_error_is_raised(self):
        Root = g.ObjectType(
            "Root",
            (
                g.field("one", type=g.Int),
            ),
        )

        graphql_query = """
            query {
                includedField: one @blah(if: false)
            }
        """

        pytest.raises(GraphQLError, lambda: _document_text_to_graph_query(graphql_query, query_type=Root))


def _document_text_to_graph_query(document_text, *, query_type, mutation_type=None, types=None, variables=None):
    schema = create_graphql_schema(query_type=query_type, mutation_type=mutation_type, types=types)
    return document_text_to_query(document_text, graphql_schema=schema, variables=variables).graph_query
