from precisely import assert_that, equal_to

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
