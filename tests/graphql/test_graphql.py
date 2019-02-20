from precisely import assert_that, contains_exactly, equal_to, has_attrs, has_feature

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

    assert_that(result, is_success(data=equal_to({"value": "resolved"})))


def test_executor():
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

    execute = graphql.executor(query_type=Root)
    result = execute(graph=graph, document_text=query)

    assert_that(result, is_success(data=equal_to({"value": "resolved"})))


def test_can_query_schema():
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))

    graph_definition = g.define_graph(resolvers=())
    graph = graph_definition.create_graph({})

    query = """
        query {
            __schema {
                queryType { name }
            }
        }
    """

    result = graphql.execute(graph=graph, document_text=query, query_type=Root)

    assert_that(result, is_success(data=equal_to({
        "__schema": {
            "queryType": {
                "name": "Root",
            },
        },
    })))


def test_can_query_schema_with_other_data():
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

    assert_that(result, is_success(data=equal_to({
        "value": "resolved",
        "__schema": {
            "queryType": {
                "name": "Root",
            },
        },
    })))


def test_when_query_is_invalid_then_result_is_invalid():
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))

    graph_definition = g.define_graph(resolvers=())
    graph = graph_definition.create_graph({})

    query = """
        query {
            bad
        }
    """

    result = graphql.execute(graph=graph, document_text=query, query_type=Root)

    assert_that(result, is_invalid(errors=contains_exactly(
        has_str('Cannot query field "bad" on type "Root".'),
    )))


def test_when_resolution_raises_graph_error_then_result_is_invalid():
    Root = g.ObjectType("Root", fields=(
        g.field("value", g.String),
    ))

    root_resolver = g.root_object_resolver(Root)

    @root_resolver.field(Root.fields.value)
    def root_resolve_value(graph, query, args):
        raise g.GraphError("BAD")

    graph_definition = g.define_graph(resolvers=(root_resolver, ))
    graph = graph_definition.create_graph({})

    query = """
        query {
            value
        }
    """

    result = graphql.execute(graph=graph, document_text=query, query_type=Root)

    assert_that(result, is_invalid(errors=contains_exactly(
        has_str("BAD"),
    )))


def is_invalid(*, errors):
    return has_attrs(errors=errors, invalid=True)


def is_success(*, data):
    return has_attrs(
        data=data,
        errors=None,
        invalid=False,
    )


def has_str(matcher):
    return has_feature("str", str, matcher)
