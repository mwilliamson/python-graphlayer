import graphlayer as g

from . import authors, books


Root = g.ObjectType(
    "Root",
    fields=(
        g.field("authors", g.ListType(authors.Author)),
        g.field("books", g.ListType(books.Book)),
    ),
)


root_resolver = g.root_object_resolver(Root)


@root_resolver.field(Root.fields.authors)
def root_resolve_authors(graph, query, args):
    return graph.resolve(authors.AuthorQuery.select(query))


@root_resolver.field(Root.fields.books)
def root_resolve_books(graph, query, args):
    return graph.resolve(books.BookQuery.select(query))


resolvers = (root_resolver,)
