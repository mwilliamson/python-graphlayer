from precisely import assert_that, contains_exactly, equal_to, has_attrs
import pytest

import graphlayer as g
import graphlayer.connections


Book = g.ObjectType(
    "Book",
    fields=lambda: (g.field("title", type=g.String),),
)


def select_books_by_id(query, ids):
    return BookQuery(type_query=query, ids=ids)


class BookQuery(object):
    def __init__(self, type_query, ids):
        self.type = BookQuery
        self.type_query = type_query
        self.ids = ids


@g.resolver(BookQuery)
@g.dependencies(books="all_books")
def resolve_books(graph, query, books):
    build_book_object = g.create_object_builder(query.type_query)

    @build_book_object.getter(Book.fields.title)
    def field_title(book):
        return book

    return {book_id: build_book_object(books[book_id]) for book_id in query.ids}


@g.dependencies(books="all_books")
def fetch_book_cursors(*, after_cursor, limit, books):
    return [
        book_id
        for book_id, book in books.items()
        if after_cursor is None or book_id > after_cursor
    ][:limit]


books_connection = graphlayer.connections.forward_connection(
    connection_type_name="BooksConnection",
    node_type=Book,
    select_by_cursor=select_books_by_id,
    cursor_encoding=graphlayer.connections.int_cursor_encoding,
    fetch_cursors=fetch_book_cursors,
)

BooksConnection = books_connection.Connection
BookEdge = books_connection.Edge
PageInfo = graphlayer.connections.PageInfo

Query = g.ObjectType(
    "Query",
    fields=lambda: (books_connection.field("books_connection"),),
)

resolve_query = g.root_object_resolver(Query)


@resolve_query.field(Query.fields.books_connection)
def resolve_query_field_books_connection(graph, query, args):
    return graph.resolve(books_connection.select_field(query, args=args))


resolvers = (resolve_books, books_connection.resolvers, resolve_query)

graph_definition = g.define_graph(resolvers)


def create_graph(books):
    return graph_definition.create_graph({"all_books": books})


def test_when_there_are_no_edges_then_connection_is_empty():
    graph = create_graph({})

    result = graph.resolve(
        Query(
            g.key(
                "books",
                Query.fields.books_connection(
                    Query.fields.books_connection.params.first(2),
                    g.key(
                        "edges",
                        BooksConnection.fields.edges(
                            g.key(
                                "node",
                                BookEdge.fields.node(
                                    g.key("title", Book.fields.title()),
                                ),
                            ),
                        ),
                    ),
                    g.key(
                        "page_info",
                        BooksConnection.fields.page_info(
                            g.key("end_cursor", PageInfo.fields.end_cursor()),
                            g.key("has_next_page", PageInfo.fields.has_next_page()),
                        ),
                    ),
                ),
            ),
        )
    )

    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(),
            page_info=has_attrs(end_cursor=None, has_next_page=False),
        ),
    )


def test_when_there_are_more_edges_than_requested_then_first_edges_are_fetched():
    graph = create_graph(
        {
            42: "Leave it to Psmith",
            43: "The Gentleman's Guide to Vice and Virtue",
            44: "Catch-22",
        }
    )

    result = graph.resolve(
        Query(
            g.key(
                "books",
                Query.fields.books_connection(
                    Query.fields.books_connection.params.first(2),
                    g.key(
                        "edges",
                        BooksConnection.fields.edges(
                            g.key(
                                "node",
                                BookEdge.fields.node(
                                    g.key("title", Book.fields.title()),
                                ),
                            ),
                        ),
                    ),
                    g.key(
                        "page_info",
                        BooksConnection.fields.page_info(
                            g.key("has_next_page", PageInfo.fields.has_next_page()),
                        ),
                    ),
                ),
            ),
        )
    )

    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Leave it to Psmith")),
                has_attrs(
                    node=has_attrs(title="The Gentleman's Guide to Vice and Virtue")
                ),
            ),
            page_info=has_attrs(has_next_page=True),
        ),
    )


def test_when_there_are_fewer_edges_than_requested_then_all_edges_are_fetched():
    graph = create_graph(
        {
            42: "Leave it to Psmith",
        }
    )

    result = graph.resolve(
        Query(
            g.key(
                "books",
                Query.fields.books_connection(
                    Query.fields.books_connection.params.first(2),
                    g.key(
                        "edges",
                        BooksConnection.fields.edges(
                            g.key(
                                "node",
                                BookEdge.fields.node(
                                    g.key("title", Book.fields.title()),
                                ),
                            ),
                        ),
                    ),
                    g.key(
                        "page_info",
                        BooksConnection.fields.page_info(
                            g.key("has_next_page", PageInfo.fields.has_next_page()),
                        ),
                    ),
                ),
            ),
        )
    )

    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Leave it to Psmith")),
            ),
            page_info=has_attrs(has_next_page=False),
        ),
    )


def test_when_there_are_exactly_number_of_edges_requested_then_all_edges_are_fetched():
    graph = create_graph(
        {
            42: "Leave it to Psmith",
            43: "The Gentleman's Guide to Vice and Virtue",
        }
    )

    result = graph.resolve(
        Query(
            g.key(
                "books",
                Query.fields.books_connection(
                    Query.fields.books_connection.params.first(2),
                    g.key(
                        "edges",
                        BooksConnection.fields.edges(
                            g.key(
                                "node",
                                BookEdge.fields.node(
                                    g.key("title", Book.fields.title()),
                                ),
                            ),
                        ),
                    ),
                    g.key(
                        "page_info",
                        BooksConnection.fields.page_info(
                            g.key("has_next_page", PageInfo.fields.has_next_page()),
                        ),
                    ),
                ),
            ),
        )
    )

    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Leave it to Psmith")),
                has_attrs(
                    node=has_attrs(title="The Gentleman's Guide to Vice and Virtue")
                ),
            ),
            page_info=has_attrs(has_next_page=False),
        ),
    )


def test_end_cursor_can_be_used_as_after_argument_to_get_next_page():
    graph = create_graph(
        {
            42: "Leave it to Psmith",
            43: "The Gentleman's Guide to Vice and Virtue",
            44: "Catch-22",
            45: "Pericles, Prince of Tyre",
            46: "Captain Corelli's Mandolin",
        }
    )

    def fetch(*, after):
        return graph.resolve(
            Query(
                g.key(
                    "books",
                    Query.fields.books_connection(
                        Query.fields.books_connection.params.first(2),
                        Query.fields.books_connection.params.after(after),
                        g.key(
                            "edges",
                            BooksConnection.fields.edges(
                                g.key(
                                    "node",
                                    BookEdge.fields.node(
                                        g.key("title", Book.fields.title()),
                                    ),
                                ),
                            ),
                        ),
                        g.key(
                            "page_info",
                            BooksConnection.fields.page_info(
                                g.key("end_cursor", PageInfo.fields.end_cursor()),
                                g.key("has_next_page", PageInfo.fields.has_next_page()),
                            ),
                        ),
                    ),
                ),
            )
        )

    result = fetch(after=None)
    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Leave it to Psmith")),
                has_attrs(
                    node=has_attrs(title="The Gentleman's Guide to Vice and Virtue")
                ),
            ),
            page_info=has_attrs(has_next_page=True),
        ),
    )

    result = fetch(after=result.books.page_info.end_cursor)
    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Catch-22")),
                has_attrs(node=has_attrs(title="Pericles, Prince of Tyre")),
            ),
            page_info=has_attrs(has_next_page=True),
        ),
    )

    result = fetch(after=result.books.page_info.end_cursor)
    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Captain Corelli's Mandolin")),
            ),
            page_info=has_attrs(has_next_page=False),
        ),
    )

    result = fetch(after=result.books.page_info.end_cursor)
    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(),
            page_info=has_attrs(end_cursor=None, has_next_page=False),
        ),
    )


def test_edge_cursor_can_be_used_as_after_argument_to_get_next_page():
    graph = create_graph(
        {
            42: "Leave it to Psmith",
            43: "The Gentleman's Guide to Vice and Virtue",
            44: "Catch-22",
        }
    )

    def fetch(*, after):
        return graph.resolve(
            Query(
                g.key(
                    "books",
                    Query.fields.books_connection(
                        Query.fields.books_connection.params.first(2),
                        Query.fields.books_connection.params.after(after),
                        g.key(
                            "edges",
                            BooksConnection.fields.edges(
                                g.key("cursor", BookEdge.fields.cursor()),
                                g.key(
                                    "node",
                                    BookEdge.fields.node(
                                        g.key("title", Book.fields.title()),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            )
        )

    result = fetch(after=None)
    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Leave it to Psmith")),
                has_attrs(
                    node=has_attrs(title="The Gentleman's Guide to Vice and Virtue")
                ),
            ),
        ),
    )

    result = fetch(after=result.books.edges[-1].cursor)
    assert_that(
        result.books,
        has_attrs(
            edges=contains_exactly(
                has_attrs(node=has_attrs(title="Catch-22")),
            ),
        ),
    )


def test_nodes_can_be_fetched_directly():
    graph = create_graph(
        {
            42: "Leave it to Psmith",
            43: "The Gentleman's Guide to Vice and Virtue",
            44: "Catch-22",
        }
    )

    result = graph.resolve(
        Query(
            g.key(
                "books",
                Query.fields.books_connection(
                    Query.fields.books_connection.params.first(2),
                    g.key(
                        "nodes",
                        BooksConnection.fields.nodes(
                            g.key("title", Book.fields.title()),
                        ),
                    ),
                    g.key(
                        "page_info",
                        BooksConnection.fields.page_info(
                            g.key("has_next_page", PageInfo.fields.has_next_page()),
                        ),
                    ),
                ),
            ),
        )
    )

    assert_that(
        result.books,
        has_attrs(
            nodes=contains_exactly(
                has_attrs(title="Leave it to Psmith"),
                has_attrs(title="The Gentleman's Guide to Vice and Virtue"),
            ),
        ),
    )


def test_when_first_is_negative_then_error_is_raised():
    graph = create_graph({})

    query = Query(
        g.key(
            "books",
            Query.fields.books_connection(
                Query.fields.books_connection.params.first(-1),
                g.key(
                    "page_info",
                    BooksConnection.fields.page_info(
                        g.key("has_next_page", PageInfo.fields.has_next_page()),
                    ),
                ),
            ),
        ),
    )

    error = pytest.raises(g.GraphError, lambda: graph.resolve(query))

    assert_that(
        str(error.value), equal_to("first must be non-negative integer, was -1")
    )
