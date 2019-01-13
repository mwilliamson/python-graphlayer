import graphlayer as g
import graphlayer.sqlalchemy as gsql

from .. import database
from . import authors


Book = g.ObjectType("Book", fields=lambda: (
    g.field("author", type=authors.Author),
    g.field("title", type=g.String),
))


class BookQuery(object):
    @staticmethod
    def select(type_query):
        return BookQuery(type_query=type_query)

    def __init__(self, type_query):
        self.type = BookQuery
        self.type_query = type_query


@g.resolver(BookQuery)
def book_resolver(graph, query):
    return graph.resolve(gsql.select(query.type_query))


book_sql_resolver = gsql.sql_table_resolver(
    Book,
    database.Book,
    fields=lambda: {
        Book.fields.author: gsql.join(
            foreign_key=(database.Book.author_id, ),
            resolve=lambda graph, field_query, ids: graph.resolve(
                authors.AuthorQuery.select_by_id(field_query.type_query, ids=ids),
            ),
        ),
        Book.fields.title: gsql.expression(database.Book.title),
    },
)


resolvers = (
    book_resolver,
    book_sql_resolver,
)
