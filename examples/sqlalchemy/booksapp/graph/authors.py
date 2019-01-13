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
        return AuthorQuery(type_query=type_query, by_ids=None)

    @staticmethod
    def select_by_id(type_query, ids):
        return AuthorQuery(type_query=type_query, by_ids=ids)

    def __init__(self, type_query, by_ids):
        self.type = AuthorQuery
        self.type_query = type_query
        self.by_ids = by_ids


@g.resolver(AuthorQuery)
def author_resolver(graph, query):
    sql_query = gsql.select(query.type_query)

    if query.by_ids is not None:
        sql_query = sql_query \
            .where(database.Author.id.in_(query.by_ids)) \
            .index_by((database.Author.id, ))

    return graph.resolve(sql_query)


author_sql_resolver = gsql.sql_table_resolver(
    Author,
    database.Author,
    fields=lambda: {
        Author.fields.name: gsql.expression(database.Author.name),
    },
)


resolvers = (
    author_resolver,
    author_sql_resolver,
)
