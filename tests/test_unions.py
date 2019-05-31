from precisely import assert_that, contains_exactly, has_attrs

import graphlayer as g
from graphlayer import unions
from .matchers import is_query


def test_can_select_unions():
    Person = g.InterfaceType(
        "Person",
        fields=lambda: (
            g.field("name", type=g.String),
        ),
    )

    Author = g.ObjectType(
        "Author",
        fields=lambda: (
            g.field("name", type=g.String),
            g.field("books_written", type=g.Int),
        ),
        interfaces=lambda: (Person, ),
    )

    Reader = g.ObjectType(
        "Reader",
        fields=lambda: (
            g.field("name", type=g.String),
            g.field("books_read", type=g.Int),
        ),
        interfaces=lambda: (Person, ),
    )

    @g.resolver(g.ListType(Author))
    def resolve_author(graph, query):
        assert_that(query, is_query(g.ListType(Author)(
            g.key("name", Author.fields.name()),
            g.key("books_written", Author.fields.books_written()),
        )))
        return [
            g.Object(dict(name="<author 1>", books_written=1)),
            g.Object(dict(name="<author 2>", books_written=2)),
        ]

    @g.resolver(g.ListType(Reader))
    def resolve_reader(graph, query):
        assert_that(query, is_query(g.ListType(Reader)(
            g.key("name", Reader.fields.name()),
            g.key("books_read", Reader.fields.books_read()),
        )))
        return [
            g.Object(dict(name="<reader 3>", books_read=3)),
            g.Object(dict(name="<reader 4>", books_read=4)),
        ]

    resolvers = (
        unions.resolver,
        resolve_author,
        resolve_reader,
    )

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({})

    query = unions.select(
        g.ListType(Person)(
            g.key("name", Person.fields.name()),
            g.key("books_read", Reader.fields.books_read()),
            g.key("books_written", Author.fields.books_written()),
        ),
        (
            # TODO: Make sure select is called
            (Author, lambda author_query: author_query),
            (Reader, lambda reader_query: reader_query),
        ),
        merge=flatten,
    )
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(name="<author 1>", books_written=1),
        has_attrs(name="<author 2>", books_written=2),
        has_attrs(name="<reader 3>", books_read=3),
        has_attrs(name="<reader 4>", books_read=4),
    ))


def flatten(values):
    return [
        element
        for value in values
        for element in value
    ]
