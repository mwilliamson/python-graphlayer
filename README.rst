High-performance library for implementing GraphQL APIs
======================================================

GraphLayer is a Python library for implementing high-performance GraphQL APIs.
By running resolve functions for each node in the request rather than each node in the response,
the overhead of asynchronous function calls is reduced.
Queries can also be written directly to fetch batches directly to avoid the N+1 problem
without intermediate layers such as DataLoader.

Why GraphQL?
------------

TODO:
* No overfetching/underfetching
* Schema allows GraphiQL, checking of queries, type generation

Why GraphLayer?
---------------

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
    from graphlayer.graphql import execute as graphql_execute
    import sqlalchemy.orm
    
    from .database import AuthorRecord, BookRecord
    
    Author = g.ObjectType("Author", fields=lambda: (
        g.field("name", type=g.String),
    ))

    author_resolver = gsql.sql_table_resolver(
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

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRecord,
        fields={
            Book.fields.title: gsql.expression(BookRecord.title),
            Book.fields.author: g.single(gsql.sql_join({
                BookRecord.author_id: AuthorRecord.id,
            })),
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

    def execute_query(query, *, variables=None, session):
        graph = graph_definition.create_graph({
            sqlalchemy.orm.Session: session,
        })
        return graphql_execute(
            query,
            graph=graph,
            variables=variables,
            query_type=Root,
        )
    
    print(execute_query(
        """
            query {
                books {
                    title
                    author { name }
                }
            }
        """,
        session=session,
    ))


Installation
------------

::

    pip install graphlayer

Tutorial
--------

This tutorial builds up a simple application using SQLAlchemy and GraphLayer.
The goal is to execute the following query:

::

    query {
        books(genre: "comedy") {
            title
            author {
                name
            }
        }
    }

That is, get the list of all books in the comedy genre,
with the title and name of the author for each book.

Getting started
~~~~~~~~~~~~~~~

Let's start with a simple query, getting the count of books:

::

    query {
        bookCount
    }

All queries share the same root object,
but can ask for whatever fields they want.
As a first step, we'll define the schema of the root object.
In this case, it has a single integer field called ``book_count``
(note that casing is automatically converted between camel case and snake case):

.. code-block:: python

    import graphlayer as g
    
    Root = g.ObjectType("Root", fields=(
        g.field("book_count", type=g.Int),
    ))

We'll also need to define how to resolve the book count by defining a resolver function.
When we define a resolver, we need to mark it as a resolver function for a particular query type.
In this case, we'll need to mark it as a resolver for the root type.
A resolver is passed two arguments: the graph and the query to resolve,
and should return a complete response with all of the fields specified in the query.
For now, we'll define a resolver that returns a fixed object,
and prints out the query so we can a take a look at it.

.. code-block:: python

    import graphlayer as g
    from graphlayer.graphql import execute
    
    Root = g.ObjectType("Root", fields=(
        g.field("book_count", type=g.Int),
    ))
    
    @g.resolver(Root)
    def resolve_root(graph, query):
        print("query:", query)
        return query.create_object({
            "bookCount": 3,
        })
    
    resolvers = (resolve_root, )
    graph_definition = g.define_graph(resolvers=resolvers)
    graph = graph_definition.create_graph({})
    
    execute(
        """
            query {
                bookCount
            }
        """,
        graph=graph,
        query_type=Root,
    )
    
Running this will print out:

::

    query: ObjectQuery(
        type=Root,
        fields=(
            FieldQuery(
                key="bookCount",
                field=Root.fields.book_count,
                type_query=scalar_query,
            ),
        ),
    )

Note that the ``FieldQuery`` has a ``key`` attribute.
Since the user can rename fields in the query,
we should use the key as passed in the field query.

.. code-block:: python

    @g.resolver(Root)
    def resolve_root(graph, query):
        field_query = query.fields[0]
    
        return query.create_object({
            field_query.key: 3,
        })

At the moment,
since only one field is defined on Root,
we can always assume that field is being requested.
However, that often won't be the case.
For instance, we could add an author count to the root:

.. code-block:: python

    Root = g.ObjectType("Root", fields=(
        g.field("author_count", type=g.Int),
        g.field("book_count", type=g.Int),
    ))

Now we'll need to check what field is being requested.

.. code-block:: python

    @g.resolver(Root)
    def resolve_root(graph, query):
        def resolve_field(field):
            if field == Root.fields.author_count:
                return 2
            elif field == Root.fields.book_count:
                return 3
            else:
                raise Exception("unknown field: {}".format(field))
                
        field_query = query.fields[0]
    
        return query.create_object({
            field_query.key: resolve_field(field_query.field),
        })

What's more, the user might request more than one field,
so we should iterate through ``query.fields``.

.. code-block:: python

    @g.resolver(Root)
    def resolve_root(graph, query):
        def resolve_field(field):
            if field == Root.fields.author_count:
                return 2
            elif field == Root.fields.book_count:
                return 3
            else:
                raise Exception("unknown field: {}".format(field))
    
        return query.create_object(dict(
            (field_query.key, resolve_field(field_query.field))
            for field_query in query.fields
        ))

If we wrap the call to ``execute`` in a ``print``:

.. code-block: python

    print("result", execute(
        """
            query {
                bookCount
            }
        """,
        graph=graph,
        query_type=Root,
    ))

Then we should get the output:

::

    result: {'bookCount': 3}

Adding SQLAlchemy
~~~~~~~~~~~~~~~~~

So far, we've returned hard-coded values.
Let's add in a database using SQLAlchemy and an in-memory SQLite database.
At the start of our script we'll add some code to set up the database schema and add data:

.. code-block:: python

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
        genre = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
        author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(AuthorRecord.id), nullable=False)

    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    session = sqlalchemy.orm.Session(engine)
    author_wodehouse = AuthorRecord(name="PG Wodehouse")
    author_bernières = AuthorRecord(name="Louis de Bernières")
    session.add_all((author_wodehouse, author_bernières))
    session.flush()
    session.add(BookRecord(title="Leave It to Psmith", genre="comedy", author_id=author_wodehouse.id))
    session.add(BookRecord(title="Right Ho, Jeeves", genre="comedy", author_id=author_wodehouse.id))
    session.add(BookRecord(title="Captain Corelli's Mandolin", genre="historical_fiction", author_id=author_bernières.id))
    session.flush()

Next, we'll update our resolvers to use the database:

.. code-block:: python

    @g.resolver(Root)
    def resolve_root(graph, query):
        def resolve_field(field):
            if field == Root.fields.author_count:
                return session.query(AuthorRecord).count()
            elif field == Root.fields.book_count:
                return session.query(BookRecord).count()
            else:
                raise Exception("unknown field: {}".format(field))
    
        return query.create_object(dict(
            (field_query.key, resolve_field(field_query.field))
            for field_query in query.fields
        ))

Adding books to the root
~~~~~~~~~~~~~~~~~~~~~~~~

So far, we've added two scalar fields to the root.
Let's add in a ``books`` field, which should be a little more interesting.
Our aim is to be able to run the query:

::

    query {
        books {
            title
        }
    }

We start by creating a ``Book`` object type,
and using it to define the ``books`` field on ``Root``:

.. code-block:: python

    Book = g.ObjectType("Book", fields=(
        g.field("title", type=g.String),
        g.field("genre", type=g.String),
    ))

    Root = g.ObjectType("Root", fields=(
        g.field("author_count", type=g.Int),
        g.field("book_count", type=g.Int),
        g.field("books", type=g.ListType(Book)),
    ))

We'll need update the root resolver to handle the new field.
Although we could handle the field directly in the root resolver,
we'll instead ask the graph to resolve the query for us.
This allows us to have a common way to resolve books,
regardless of where they appear in the query.

.. code-block:: python

    @g.resolver(Root)
    def resolve_root(graph, query):
        def resolve_field(field_query):
            if field_query.field == Root.fields.author_count:
                return session.query(AuthorRecord).count()
            elif field_query.field == Root.fields.book_count:
                return session.query(BookRecord).count()
            elif field_query.field == Root.fields.books:
                return graph.resolve(field_query.type_query)
            else:
                raise Exception("unknown field: {}".format(field_query.field))
    
        return query.create_object(dict(
            (field_query.key, resolve_field(field_query))
            for field_query in query.fields
        ))

This means we need to define a resolver for a list of books.
For now, let's just print the query and return an empty list so we can see what the query looks like.

.. code-block:: python

    @g.resolver(g.ListType(Book))
    def resolve_books(graph, query):
        print("books query", query)
        return []

    resolvers = (resolve_root, resolve_books)

If update the query we pass to ``execute``:

.. code-block:: python

    print("result", execute(
        """
            query {
                books {
                    title
                }
            }
        """,
        graph=graph,
        query_type=Root,
    ))

Then our script should now produce the output:

::

    books query: ListQuery(
        type=List(Book),
        element_query=ObjectQuery(
            type=Book,
            fields=(
                FieldQuery(
                    key="title",
                    field=Book.fields.title,
                    type_query=scalar_query,
                ),
            ),
        ),
    )
    result: {'books': []}

Similarly to the ``ObjectQuery`` we had when resolving the root object,
we have an ``ObjectQuery`` for ``Book``.
Since a list is being requested, this is then wrapped in a ``ListQuery``,
with the object query being accessible through the ``element_query`` attribute.

We can write a resolver for a list of books by first fetching all of the books,
and then mapping each fetched book to an object according to the fields requested in the query.

.. code-block:: python

    @g.resolver(g.ListType(Book))
    def resolve_books(graph, query):
        books = session.query(BookRecord.title, BookRecord.genre).all()
    
        def resolve_field(book, field):
            if field == Book.fields.title:
                return book.title
            elif field == Book.fields.genre:
                return book.genre
            else:
                raise Exception("unknown field: {}".format(field))
    
        return [
            query.element_query.create_object(dict(
                (field_query.key, resolve_field(book, field_query.field))
                for field_query in query.element_query.fields
            ))
            for book in books
        ]

Running this code should give the output:

::

    result {'books': [{'title': 'Leave It to Psmith'}, {'title': 'Right Ho, Jeeves'}, {'title': "Captain Corelli's Mandolin"}]}

We can make the resolver more efficient by only fetching those columns required by the query.
Although this makes comparatively little difference with the data we have at the moment,
this can help improve performance when there are many more fields the user can request,
and with larger data sets.

.. code-block:: python

    @g.resolver(g.ListType(Book))
    def resolve_books(graph, query):
        field_to_expression = {
            Book.fields.title: BookRecord.title,
            Book.fields.genre: BookRecord.genre,
        }
        
        expressions = frozenset(
            field_to_expression[field_query.field]
            for field_query in query.element_query.fields
        )
    
        books = session.query(*expressions).all()
    
        def resolve_field(book, field):
            if field == Book.fields.title:
                return book.title
            elif field == Book.fields.genre:
                return book.genre
            else:
                raise Exception("unknown field: {}".format(field))
    
        return [
            query.element_query.create_object(dict(
                (field_query.key, resolve_field(book, field_query.field))
                for field_query in query.element_query.fields
            ))
            for book in books
        ]

Adding a genre argument to the books field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adding an author field to books
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dependency injection
~~~~~~~~~~~~~~~~~~~~

Extracting duplication
~~~~~~~~~~~~~~~~~~~~~~

TODO: update the following (extracted from earlier)

In order to accommodate the flexibility in queries,
we've had to do a lot of work,
when all we really want to do was say
"the author count field should be resolved to 2 and the book count field should be resolved to 3".
Since a lot of the work is not specific to this domain,
we can extract it out into another function to help us build resolvers.
For root objects, the ``root_object_resolver()`` is such a function.

.. code-block:: python

    resolve_root = g.root_object_resolver(Root)
    
    @resolve_root.field(Root.fields.author_count)
    def root_resolve_author_count(graph, query, args):
        return 2
    
    @resolve_root.field(Root.fields.book_count)
    def root_resolve_book_count(graph, query, args):
        return 3
