from precisely import assert_that, equal_to

import graphlayer.core as g


def test_resolver_is_dispatched_using_type_of_query():
    @g.resolver("one")
    def resolve_one(graph, query):
        return 1

    @g.resolver("two")
    def resolve_two(graph, query):
        return 2

    resolvers = [resolve_one, resolve_two]

    class Query(object):
        type = "one"

    result = g.create_graph(resolvers).resolve(Query)

    assert_that(result, equal_to(1))


def test_when_resolve_is_called_then_resolver_is_passed_the_graph():
    @g.resolver("root")
    def resolve_root(graph, query):
        return graph.resolve(Query("leaf"))

    @g.resolver("leaf")
    def resolve_leaf(graph, query):
        return 42

    class Query(object):
        def __init__(self, type):
            self.type = type

    resolvers = [resolve_root, resolve_leaf]

    result = g.create_graph(resolvers).resolve(Query("root"))

    assert_that(result, equal_to(42))
