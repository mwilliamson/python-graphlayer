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
            "one": is_field_query(type_query=schema.scalar_query),
        }),
    ))


is_object_query = has_attrs
is_field_query = has_attrs
