from precisely import assert_that, has_attrs

import graphlayer as g


class TestObjectBuilder(object):
    def test_object_builder_creates_object_using_field_resolvers(self):
        User = g.ObjectType("User", fields=(
            g.field("name", type=g.String),
            g.field("email_address", type=g.String),
        ))

        object_builder = g.create_object_builder(User(
            g.key("n", User.fields.name()),
            g.key("e", User.fields. email_address()),
        ))

        @object_builder.getter(User.fields.name)
        def resolve_name(user):
            return user["name"]

        @object_builder.getter(User.fields.email_address)
        def resolve_email_address(user):
            return user["emailAddress"]

        result = object_builder({"name": "Bob", "emailAddress": "bob@example.com"})
        assert_that(result, has_attrs(
            n="Bob",
            e="bob@example.com",
        ))

    def test_field_resolvers_can_be_defined_using_field_name(self):
        User = g.ObjectType("User", fields=(
            g.field("name", type=g.String),
        ))

        object_builder = g.create_object_builder(User(
            g.key("n", User.fields.name()),
        ))

        @object_builder.getter("name")
        def resolve_name(user):
            return user["name"]

        result = object_builder({"name": "Bob"})
        assert_that(result, has_attrs(
            n="Bob",
        ))


class TestRootResolver(object):
    def test_root_object_resolver_can_resolve_fields_with_dependencies(self):
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


    def test_root_object_resolver_passes_arguments_to_field_resolvers(self):
        Root = g.ObjectType("Root", fields=(
            g.field("value", type=g.Int, params=(
                g.param("answer", type=g.Int),
            )),
        ))

        resolve_root = g.root_object_resolver(Root)

        @resolve_root.field(Root.fields.value)
        def root_resolve_value(graph, query, args):
            return args.answer

        graph_definition = g.define_graph(resolvers=(resolve_root, ))
        graph = graph_definition.create_graph({})

        query = Root(
            g.key("value", Root.fields.value(Root.fields.value.params.answer(42))),
        )
        assert_that(graph.resolve(query), has_attrs(value=42))
