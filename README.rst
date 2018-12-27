High-performance library for implementing GraphQL APIs
======================================================

What causes GraphQL APIs to be slow?
In most implementations of GraphQL,
resolve functions are run for each node in the response.
This can lead to poor performance for two main reasons.
The first is the N+1 problem.
The second is the overhead of calling a potentially asynchronous resolve function for every node in the response.
Although the overhead per call is small,
for large datasets, the sum of this overhead can be the vast majority of the time to respond.

GraphLayer suggests instead that resolve functions could be called according to the shape of the request rather than the response.
This avoids the N+1 problem without introducing additional complexity,
such as batching requests in the manner of DataLoader and similar libraries,
and allowing resolve functions to be written in a style that more naturally maps to data stores such as SQL databases.
Secondly, although there's still the overhead of calling resolve functions,
this overhead is multipled by the number of the nodes in the request rather than the response:
for large datasets, this is a considerable saving.

As a concrete example, consider the query:

::

    query {
        books {
            title
            author {
                name
            }
        }
    }

A naive GraphQL implementation would issue one SQL query to get the list of all books,
then N queries to get the author of each book.
Using DataLoader, the N queries to get the author of each book would be combined into a single query.
Using GraphLayer, there would be a single query to get the authors without any batching.

As a quick example, the below would allow the example query to be executed,
assuming SQLAlchemy has already been set up.
A more detailed explanation of how GraphLayer works and how to use it follows.

.. code-block:: python

    import graphlayer as g
    from graphlayer import sqlalchemy as gsql
    import sqlalchemy.orm
    
    from .database import AuthorRecord, BookRecord
    
    Author = g.ObjectType("Author", fields=lambda: (
        g.field("name", type=g.String),
    ))
    
    author_resolver = gsql.sql_table(
        Author,
        AuthorRecord,
        fields={
            Author.fields.name: gsql.expression(AuthorRecord.name),
        },
    )
    
    Book = g.ObjectType("Book", fields=lambda: (
        g.field("title", type=g.String),
        g.field("author", type=Author),
    ))
    
    book_resolver = gsql.sql_table(
        Book,
        BookRecord,
        fields={
            Book.fields.title: gsql.expression(BookRecord.title),
            Book.fields.author: gsql.sql_join({
                BookRecord.author_id: AuthorRecord.id,
            }),
        },
    )
    
    Root = g.ObjectType("Root", fields=lambda: (
        g.field("books", type=g.ListType(Book)),
    ))
    
    root_resolver = g.root_object_resolver(Root)
    
    @root_resolver.field(Root.fields.books)
    def root_resolve_books(graph, query, args):
        return graph.resolve(gsql.select(query))
    
    resolvers = (author_resolver, book_resolver, root_resolver)
    graph_definition = g.define_graph(resolvers=resolvers)
    
    def execute_query(query, variables, session):
        graph = graph_definition.create_graph({
            sqlalchemy.orm.Session: session,
        })
        return graphql_execute(
            graph=graph,
            document_text=query,
            variables=variables,
            query_type=Root,
        )

Installation
------------

::

    pip install graphlayer
