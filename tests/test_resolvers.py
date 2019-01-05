from precisely import assert_that, has_attrs

import graphlayer as g


def test_root_object_resolver_can_resolve_fields_with_dependencies():
    Root = g.ObjectType("Root", fields=(
        g.field("value", type=g.Int),
    ))

    resolve_root = g.root_object_resolver(Root)

    value_key = object()

    @resolve_root.field(Root.fields.value)
    @g.dependencies(value=value_key)
    def root_resolve_value(graph, query, args, *, value):
        return value

    graph_definition = g.define_graph(resolvers=(resolve_root, ))
    graph = graph_definition.create_graph({value_key: 42})

    query = Root(
        g.key("value", Root.fields.value()),
    )
    assert_that(graph.resolve(query), has_attrs(value=42))
