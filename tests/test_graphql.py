from precisely import assert_that, has_attrs, is_mapping

import graphlayer as g
from graphlayer import schema
from graphlayer.graphql import document_text_to_query


def test_simple_query_is_converted_to_object_query():
    Root = g.ObjectType(
        "Root",
        (
            g.field("one", type=g.IntType),
        ),
    )
    
    graphql_query = """
        query {
            one
        }
    """
    
    object_query = document_text_to_query(graphql_query, query_type=Root)
    
    assert_that(object_query, is_object_query(
        type=Root,
        fields=is_mapping({
            "one": is_field_query(
                field=is_field(name="one"),
                type_query=schema.scalar_query,
            ),
        }),
    ))


def test_fields_can_have_alias():
    Root = g.ObjectType(
        "Root",
        (
            g.field("one", type=g.IntType),
        ),
    )
    
    graphql_query = """
        query {
            value: one
        }
    """
    
    object_query = document_text_to_query(graphql_query, query_type=Root)
    
    assert_that(object_query, is_object_query(
        type=Root,
        fields=is_mapping({
            "value": is_field_query(
                field=is_field(name="one"),
                type_query=schema.scalar_query,
            ),
        }),
    ))


def test_field_names_are_converted_to_snake_case():
    Root = g.ObjectType(
        "Root",
        (
            g.field("one_value", type=g.IntType),
        ),
    )
    
    graphql_query = """
        query {
            oneValue
        }
    """
    
    object_query = document_text_to_query(graphql_query, query_type=Root)
    
    assert_that(object_query, is_object_query(
        type=Root,
        fields=is_mapping({
            "oneValue": is_field_query(
                field=is_field(name="one_value"),
                type_query=schema.scalar_query,
            ),
        }),
    ))


is_object_query = has_attrs
is_field_query = has_attrs
is_field = has_attrs