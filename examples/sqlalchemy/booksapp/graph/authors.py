import graphlayer as g
import graphlayer.sqlalchemy as gsql

from .. import database
from . import books


Author = g.ObjectType("Author", fields=lambda: (
    g.field("books", type=g.ListType(books.Book)),
    g.field("name", type=g.String),
))


class AuthorQuery(object):
    @staticmethod
    def select(type_query):
        return gsql.select(type_query)

    @staticmethod
    def select_by_id(type_query, ids):
        return AuthorQuery.select(type_query).by(database.Author.id, ids)


author_sql_resolver = gsql.sql_table_resolver(
    Author,
    database.Author,
    fields=lambda: {
        Author.fields.books: gsql.join(
            expressions=(database.Author.id, ),
            resolve=lambda graph, field_query, ids: graph.resolve(
                books.BookQuery.select_by_author_ids(field_query.type_query, author_ids=ids),
            ),
        ),
        Author.fields.name: gsql.expression(database.Author.name),
    },
)


resolvers = (
    author_sql_resolver,
)
