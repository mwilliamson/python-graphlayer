import graphlayer as g
from graphlayer import sqlalchemy as gsql
from graphlayer.graphql import execute as graphql_execute
import sqlalchemy.ext.declarative
import sqlalchemy.orm


Base = sqlalchemy.ext.declarative.declarative_base()


class AuthorRecord(Base):
    __tablename__ = "author"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)


class BookRecord(Base):
    __tablename__ = "book"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
    author_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey(AuthorRecord.id), nullable=False
    )


Author = g.ObjectType("Author", fields=lambda: (g.field("name", type=g.String),))

author_resolver = gsql.sql_table_resolver(
    Author,
    AuthorRecord,
    fields={
        Author.fields.name: gsql.expression(AuthorRecord.name),
    },
)

Book = g.ObjectType(
    "Book",
    fields=lambda: (
        g.field("title", type=g.String),
        g.field("author", type=Author),
    ),
)

book_resolver = gsql.sql_table_resolver(
    Book,
    BookRecord,
    fields={
        Book.fields.title: gsql.expression(BookRecord.title),
        Book.fields.author: g.single(
            gsql.sql_join(
                {
                    BookRecord.author_id: AuthorRecord.id,
                }
            )
        ),
    },
)

Root = g.ObjectType("Root", fields=lambda: (g.field("books", type=g.ListType(Book)),))

root_resolver = g.root_object_resolver(Root)


@root_resolver.field(Root.fields.books)
def root_resolve_books(graph, query, args):
    return graph.resolve(gsql.select(query))


resolvers = (author_resolver, book_resolver, root_resolver)
graph_definition = g.define_graph(resolvers=resolvers)


def execute_query(query, *, variables=None, session):
    graph = graph_definition.create_graph(
        {
            sqlalchemy.orm.Session: session,
        }
    )
    return graphql_execute(
        query,
        graph=graph,
        variables=variables,
        query_type=Root,
    )


engine = sqlalchemy.create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

session = sqlalchemy.orm.Session(engine)
author_1 = AuthorRecord(name="a1")
author_2 = AuthorRecord(name="a2")
session.add_all((author_1, author_2))
session.flush()
book_1 = BookRecord(title="b1", author_id=author_1.id)
book_2 = BookRecord(title="b2", author_id=author_2.id)
session.add_all((book_1, book_2))
session.flush()


print(
    execute_query(
        """
        query {
            books {
                title
                author { name }
            }
        }
    """,
        session=session,
    )
)
