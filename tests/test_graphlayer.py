from precisely import assert_that, contains_exactly, has_attrs

import graphlayer as g
from graphlayer import iterables


def test_can_get_scalar_from_root():
    Root = g.ObjectType(
        "Root",
        fields=[
            g.field("one", type=g.Int),
            g.field("two", type=g.Int),
        ],
    )

    @g.resolver(Root)
    def resolve_root(graph, query):
        values = dict(
            one=1,
            two=2,
        )

        return query.create_object(iterables.to_dict(
            (field_query.key, values[field_query.field.name])
            for field_query in query.field_queries
        ))

    resolvers = [resolve_root]

    query = Root(
        g.key("value", Root.fields.one()),
    )
    result = g.create_graph(resolvers).resolve(query)

    assert_that(result, has_attrs(value=1))


def test_constant_object_resolver():
    Root = g.ObjectType(
        "Root",
        fields=[
            g.field("one", type=g.Int),
            g.field("two", type=g.Int),
        ],
    )

    resolve_root = g.constant_object_resolver(Root, dict(one=1, two=2))

    resolvers = [resolve_root]

    query = Root(
        g.key("value", Root.fields.one()),
    )
    result = g.create_graph(resolvers).resolve(query)

    assert_that(result, has_attrs(value=1))


def test_can_recursively_resolve():
    Root = g.ObjectType(
        "Root",
        fields=lambda: [
            g.field("books", type=g.ListType(Book)),
        ],
    )

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    @g.resolver(Root)
    def resolve_root(graph, query):
        return query.create_object(iterables.to_dict(
            (field_query.key, graph.resolve(field_query.type_query))
            for field_query in query.field_queries
        ))

    @g.resolver(g.ListType(Book))
    def resolve_book(graph, query):
        books = [
            dict(title="Leave it to Psmith"),
            dict(title="Pericles, Prince of Tyre"),
        ]
        return [
            query.element_query.create_object(iterables.to_dict(
                (field_query.key, book[field_query.field.name])
                for field_query in query.element_query.field_queries
            ))
            for book in books
        ]

    resolvers = [resolve_root, resolve_book]

    query = Root(
        g.key("books", Root.fields.books(
            g.key("title", Book.fields.title()),
        )),
    )
    result = g.create_graph(resolvers).resolve(query)

    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(title="Leave it to Psmith"),
            has_attrs(title="Pericles, Prince of Tyre"),
        ),
    ))


def test_can_recursively_resolve_selected_fields():
    Root = g.ObjectType(
        "Root",
        fields=lambda: [
            g.field("books", type=g.ListType(Book)),
        ],
    )

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("author", type=Author),
            g.field("title", type=g.String),
        ],
    )

    Author = g.ObjectType(
        "Author",
        fields=lambda: [
            g.field("name", type=g.String),
        ],
    )

    @g.resolver(Root)
    def resolve_root(graph, query):
        return query.create_object(iterables.to_dict(
            (field_query.key, graph.resolve(field_query.type_query))
            for field_query in query.field_queries
        ))

    books = [
        dict(author_id="wodehouse", title="Leave it to Psmith"),
        dict(author_id="shakespeare", title="Pericles, Prince of Tyre"),
    ]

    def resolve_title(graph, book, query):
        return book["title"]

    class AuthorQuery(object):
        type = "author"

        def __init__(self, type_query, author_id):
            self.type_query = type_query
            self.author_id = author_id

    def resolve_author(graph, book, query):
        return graph.resolve(AuthorQuery(query, author_id=book["author_id"]))

    fields = {
        "title": resolve_title,
        "author": resolve_author,
    }

    def resolve_field(graph, book, field_query):
        return fields[field_query.field.name](graph, book, field_query.type_query)

    @g.resolver(g.ListType(Book))
    def resolve_book(graph, query):
        return [
            query.element_query.create_object(iterables.to_dict(
                (field_query.key, resolve_field(graph, book, field_query))
                for field_query in query.element_query.field_queries
            ))
            for book in books
        ]

    authors = {
        "wodehouse": dict(name="PG Wodehouse"),
        "shakespeare": dict(name="William Shakespeare"),
    }

    @g.resolver(AuthorQuery.type)
    def resolve_author(graph, query):
        author = authors[query.author_id]
        return query.type_query.create_object(iterables.to_dict(
            (field_query.key, author[field_query.field.name])
            for field_query in query.type_query.field_queries
        ))

    resolvers = [resolve_root, resolve_book, resolve_author]

    query = Root(
        g.key("books", Root.fields.books(
            g.key("author", Book.fields.author(
                g.key("name", Author.fields.name()),
            )),
            g.key("title", Book.fields.title()),
        )),
    )
    result = g.create_graph(resolvers).resolve(query)

    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(
                author=has_attrs(name="PG Wodehouse"),
                title="Leave it to Psmith",
            ),
            has_attrs(
                author=has_attrs(name="William Shakespeare"),
                title="Pericles, Prince of Tyre",
            ),
        ),
    ))
