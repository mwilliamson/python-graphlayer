from graphql import GraphQLError
from precisely import assert_that, equal_to
import pytest

import graphlayer as g
from graphlayer import graphql


def test_execute():
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))
    
    root_resolver = g.root_object_resolver(Root)
    
    @root_resolver.field(Root.fields.value)
    def root_resolve_value(graph, query, args):
        return "resolved"
    
    graph_definition = g.define_graph(resolvers=(root_resolver, ))
    graph = graph_definition.create_graph({})
    
    query = """
        query {
            value
        }
    """
    
    result = graphql.execute(graph=graph, document_text=query, query_type=Root)
    
    assert_that(result, equal_to({"value": "resolved"}))


def test_can_query_schema():
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))
    
    root_resolver = g.root_object_resolver(Root)
    
    @root_resolver.field(Root.fields.value)
    def root_resolve_value(graph, query, args):
        return "resolved"
    
    graph_definition = g.define_graph(resolvers=(root_resolver, ))
    graph = graph_definition.create_graph({})
    
    query = """
        query {
            value
            __schema {
                queryType { name }
            }
        }
    """
    
    result = graphql.execute(graph=graph, document_text=query, query_type=Root)
    
    assert_that(result, equal_to({
        "value": "resolved",
        "__schema": {
            "queryType": {
                "name": "Root",
            },
        },
    }))


def test_query_is_validated():
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))
    
    graph_definition = g.define_graph(resolvers=())
    graph = graph_definition.create_graph({})
    
    query = """
        {
            x
        }
    """

    error = pytest.raises(GraphQLError, lambda: graphql.execute(graph=graph, document_text=query, query_type=Root))
    assert_that(str(error.value), equal_to(('Cannot query field "x" on type "Root".')))
