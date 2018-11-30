from precisely import assert_that, equal_to

import graphlayer.core as g


def test_expander_is_dispatched_using_type_of_query():
    @g.expander("one")
    def expand_one(graph, query):
        return 1
    
    @g.expander("two")
    def expand_two(graph, query):
        return 2
    
    expanders = [expand_one, expand_two]
    
    class Query(object):
        type = "one"
    
    result = g.create_graph(expanders).expand(Query)
    
    assert_that(result, equal_to(1))


def test_when_expand_is_called_then_expander_is_passed_the_graph():
    @g.expander("root")
    def expand_root(graph, query):
        return graph.expand(Query("leaf"))
    
    @g.expander("leaf")
    def expand_leaf(graph, query):
        return 42
        
    class Query(object):
        def __init__(self, type):
            self.type = type
    
    expanders = [expand_root, expand_leaf]
    
    result = g.create_graph(expanders).expand(Query("root"))
    
    assert_that(result, equal_to(42))
