import graphlayer as g
import sqlalchemy.orm

from . import authors, books, root


resolvers = (
    authors.resolvers,
    books.resolvers,
    root.resolvers,
)


_graph_definition = g.define_graph(resolvers=resolvers)


def create_graph(*, session):
    return _graph_definition.create_graph(
        {
            sqlalchemy.orm.Session: session,
        }
    )


Root = root.Root
