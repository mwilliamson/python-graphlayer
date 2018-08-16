from precisely import assert_that, equal_to

import graphlayer.core as g


def test_given_expander_has_no_dependencies_when_expand_is_called_with_no_dependencies_then_expander_is_directly_called():
    @g.expander("root", "integer_representation")
    def expand_root(graph, query):
        return 42
    
    expanders = [expand_root]
    
    class Query(object):
        type = "root"
    
    result = g.create_graph(expanders).expand(Query, "integer_representation")
    
    assert_that(result, equal_to(42))


def test_when_expand_is_called_then_expander_is_passed_query():
    @g.expander("root", "integer_representation")
    def expand_root(graph, query):
        return query.value
    
    expanders = [expand_root]
    
    class Query(object):
        type = "root"
        value = 42
    
    result = g.create_graph(expanders).expand(Query, "integer_representation")
    
    assert_that(result, equal_to(42))


def test_when_expand_is_called_then_expander_is_passed_the_graph():
    @g.expander("root", "integer_representation")
    def expand_root(graph, query):
        return graph.expand(LeafQuery, "integer_representation")
    
    @g.expander("leaf", "integer_representation")
    def expand_leaf(graph, query):
        return query.value
    
    expanders = [expand_root, expand_leaf]
    
    class RootQuery(object):
        type = "root"
    
    class LeafQuery(object):
        type = "leaf"
        value = 47
    
    result = g.create_graph(expanders).expand(RootQuery, "integer_representation")
    
    assert_that(result, equal_to(47))
