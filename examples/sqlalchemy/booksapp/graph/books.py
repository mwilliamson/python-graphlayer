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
        return gsql.select(type_query)

    @staticmethod
    def select_by_author_ids(type_query, author_ids):
        return gsql.select(type_query).by(database.Book.author_id, author_ids)


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
    book_sql_resolver,
)
