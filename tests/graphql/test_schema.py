import graphql
from precisely import all_of, assert_that, equal_to, has_attrs, is_instance

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


is_graphql_boolean = equal_to(graphql.GraphQLBoolean)
is_graphql_float = equal_to(graphql.GraphQLFloat)
is_graphql_int = equal_to(graphql.GraphQLInt)
is_graphql_string = equal_to(graphql.GraphQLString)


def is_graphql_list(element_matcher):
    return all_of(
        is_instance(graphql.GraphQLList),
        has_attrs(of_type=element_matcher)
    )


def is_graphql_non_null(element_matcher):
    return all_of(
        is_instance(graphql.GraphQLNonNull),
        has_attrs(of_type=element_matcher)
    )
