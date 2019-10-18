import types

from precisely import assert_that, equal_to, has_attrs
import pytest

import graphlayer as g
from graphlayer import schema


class TestObjectBuilder(object):
    def test_object_builder_creates_object_using_field_resolvers(self):
        User = g.ObjectType("User", fields=(
            g.field("name", type=g.String, params=(
                g.param("truncate", type=g.Int, default=None),
            )),
        ))

        object_builder = g.create_object_builder(User(
            g.key("name", User.fields.name()),
            g.key("initial", User.fields.name(User.fields.name.params.truncate(1))),
        ))

        @object_builder.field(User.fields.name)
        def resolve_name(field_query):
            if field_query.args.truncate is None:
                return lambda user: user["name"]
            else:
                return lambda user: user["name"][:field_query.args.truncate]

        result = object_builder({"name": "Bob"})
        assert_that(result, has_attrs(
            name="Bob",
            initial="B",
        ))

    def test_object_builder_getters_access_value_directly(self):
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

    def test_attr_uses_attr_name_to_resolve_field(self):
        User = g.ObjectType("User", fields=(
            g.field("name", type=g.String),
            g.field("email_address", type=g.String),
        ))

        object_builder = g.create_object_builder(User(
            g.key("n", User.fields.name()),
            g.key("e", User.fields. email_address()),
        ))

        object_builder.attr(User.fields.name, "name")
        object_builder.attr(User.fields.email_address, "email")

        result = object_builder(types.SimpleNamespace(name="Bob", email="bob@example.com"))
        assert_that(result, has_attrs(
            n="Bob",
            e="bob@example.com",
        ))

    def test_constant_uses_value_to_resolve_field(self):
        User = g.ObjectType("User", fields=(
            g.field("name", type=g.String),
            g.field("email_address", type=g.String),
        ))

        object_builder = g.create_object_builder(User(
            g.key("n", User.fields.name()),
            g.key("e", User.fields. email_address()),
        ))

        object_builder.constant(User.fields.name, "Bob")
        object_builder.constant(User.fields.email_address, "bob@example.com")

        result = object_builder(None)
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

    def test_when_type_is_object_then_typename_field_is_resolved(self):
        User = g.ObjectType("User", fields=(
            g.field("name", type=g.String),
        ))

        object_builder = g.create_object_builder(User(
            g.key("type", schema.typename_field()),
        ))

        result = object_builder({})
        assert_that(result, has_attrs(
            type="User",
        ))

    def test_when_type_is_interface_then_typename_field_is_unresolved(self):
        User = g.InterfaceType("User", fields=(
            g.field("name", type=g.String),
        ))

        object_builder = g.create_object_builder(User(
            g.key("type", schema.typename_field()),
        ))

        error = pytest.raises(g.GraphError, lambda: object_builder({}))
        assert_that(str(error.value), equal_to("Resolver missing for field type_name"))


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
