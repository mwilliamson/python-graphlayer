High-performance library for implementing GraphQL APIs
======================================================

GraphLayer is a Python library for implementing high-performance GraphQL APIs.
By running resolve functions for each node in the request rather than each node in the response,
the overhead of asynchronous function calls is reduced.
Queries can also be written directly to fetch batches directly to avoid the N+1 problem
without intermediate layers such as DataLoader.

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

Installation
------------

::

    pip install git+https://github.com/mwilliamson/python-graphlayer.git#egg=graphlayer[graphql]

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

In this tutorial, we'll build up the necessary code from scratch,
using only the core of GraphLayer, to give an understanding of how GraphLayer works.
In practice, there are a number of helper functions that make implementation much simpler.
We'll see how to write our example using those helpers at the end.

Environment
~~~~~~~~~~~

You'll need a Python environment with at least Python 3.5 installed,
with graphlayer, graphql, and SQLAlchemy installed.
For instance, on the command line:

::

    python3 -m venv .venv
    . .venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install git+https://github.com/mwilliamson/python-graphlayer.git#egg=graphlayer[graphql]
    pip install SQLAlchemy

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
For now, we'll define a single integer field called ``book_count``
(note that casing is automatically converted between camel case and snake case):

.. code-block:: python

    import graphlayer as g

    Root = g.ObjectType("Root", fields=(
        g.field("book_count", type=g.Int),
    ))

We'll also need to define how to resolve the book count by defining a resolver function.
Each resolver function takes the graph and a query of a particular type,
and returns the result of that query.
The decorator ``g.resolver()`` is used to mark which type of query a resolver is for.
In this case, we'll need create a resolver for the root type.
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
        field_queries=(
            FieldQuery(
                key="bookCount",
                field=Root.fields.book_count,
                type_query=ScalarQuery(type=Int),
                args=(),
            ),
        ),
    )

Note that the ``FieldQuery`` has a ``key`` attribute.
Since the user can rename fields in the query,
we should use the key as passed in the field query.


.. code-block:: python

    @g.resolver(Root)
    def resolve_root(graph, query):
        field_query = query.field_queries[0]

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

        field_query = query.field_queries[0]

        return query.create_object({
            field_query.key: resolve_field(field_query.field),
        })

What's more, the user might request more than one field,
so we should iterate through ``query.field_queries`` when generating the result.


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
            for field_query in query.field_queries
        ))

If we print the data from the execution result:


.. code-block:: python

    print("result:", execute(
        """
            query {
                bookCount
            }
        """,
        graph=graph,
        query_type=Root,
    ).data)

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
            for field_query in query.field_queries
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

We'll need to update the root resolver to handle the new field.
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
            for field_query in query.field_queries
        ))

This means we need to define a resolver for a list of books.
For now, let's just print the query and return an empty list so we can see what the query looks like.



.. code-block:: python

    @g.resolver(g.ListType(Book))
    def resolve_books(graph, query):
        print("books query:", query)
        return []

    resolvers = (resolve_root, resolve_books)

If update the query we pass to ``execute``:


.. code-block:: python

    print("result:", execute(
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
            field_queries=(
                FieldQuery(
                    key="title",
                    field=Book.fields.title,
                    type_query=ScalarQuery(type=String),
                    args=(),
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
                for field_query in query.element_query.field_queries
            ))
            for book in books
        ]

Running this code should give the output:

::

    result: {'books': [{'title': 'Leave It to Psmith'}, {'title': 'Right Ho, Jeeves'}, {'title': "Captain Corelli's Mandolin"}]}

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
            for field_query in query.element_query.field_queries
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
                for field_query in query.element_query.field_queries
            ))
            for book in books
        ]

Adding a genre parameter to the books field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

So far, the ``books`` field returns all of the books in the database.
Let's add an optional ``genre`` parameter, so we can run the following query:

::

    query {
        books(genre: "comedy") {
            title
        }
    }

Before we start actually adding the parameter,
we need to make a change to how books are resolved.
At the moment, the code resolves queries for lists of books,
which doesn't provide a convenient way for us to tell the resolver to only fetch a subset of books.
To solve this, we'll wrap the object query in our own custom query class.


.. code-block:: python

    class BookQuery(object):
        def __init__(self, object_query):
            self.type = (BookQuery, object_query.type)
            self.object_query = object_query

We can then create a ``BookQuery`` in the root resolver:



.. code-block:: python

    elif field_query.field == Root.fields.books:
        return graph.resolve(BookQuery(field_query.type_query.element_query))

And we'll have to update ``resolve_books`` accordingly.
Specifically, we need to replace ``g.resolver(g.ListType(Book))`` with ``g.resolver((BookQuery, Book))``,
and replace ``query.element_query`` with ``query.object_query``.


.. code-block:: python

    @g.resolver((BookQuery, Book))
    def resolve_books(graph, query):
        field_to_expression = {
            Book.fields.title: BookRecord.title,
            Book.fields.genre: BookRecord.genre,
        }

        expressions = frozenset(
            field_to_expression[field_query.field]
            for field_query in query.object_query.field_queries
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
            query.object_query.create_object(dict(
                (field_query.key, resolve_field(book, field_query.field))
                for field_query in query.object_query.field_queries
            ))
            for book in books
        ]

Now we can get on with actually adding the parameter.
We'll first need to update the definition of the ``books`` field on ``Root``:


.. code-block:: python

    Root = g.ObjectType("Root", fields=(
        g.field("author_count", type=g.Int),
        g.field("book_count", type=g.Int),
        g.field("books", type=g.ListType(Book), params=(
            g.param("genre", type=g.String, default=None),
        )),
    ))

Next, we'll update ``BookQuery`` to support filtering by adding a ``where`` method:


.. code-block:: python

    class BookQuery(object):
        def __init__(self, object_query, genre=None):
            self.type = (BookQuery, object_query.type)
            self.object_query = object_query
            self.genre = genre

        def where(self, *, genre):
            return BookQuery(self.object_query, genre=genre)

We can use this ``where`` method when resolving the ``books`` field in the root resolver.



.. code-block:: python

    elif field_query.field == Root.fields.books:
        book_query = BookQuery(field_query.type_query.element_query)

        if field_query.args.genre is not None:
            book_query = book_query.where(genre=field_query.args.genre)

        return graph.resolve(book_query)

Finally, we need to filter the books we fetch from the database.
We'll replace:

.. code-block:: python

    books = session.query(*expressions).all()

with:


.. code-block:: python

    sqlalchemy_query = session.query(*expressions)

    if query.genre is not None:
        sqlalchemy_query = sqlalchemy_query.filter(BookRecord.genre == query.genre)

    books = sqlalchemy_query.all()

If we update our script with the new query:


.. code-block:: python

    print("result:", execute(
        """
            query {
                books(genre: "comedy") {
                    title
                }
            }
        """,
        graph=graph,
        query_type=Root,
    ))

We should see only books in the comedy genre in the output:

::

    result: {'books': [{'title': 'Leave It to Psmith'}, {'title': 'Right Ho, Jeeves'}]}

Adding authors to the root
~~~~~~~~~~~~~~~~~~~~~~~~~~

Similarly to the ``books`` field on the root,
we can add an ``authors`` field to the root.
We start by defining the ``Author`` object type,
and adding the ``authors`` field to ``Root``.


.. code-block:: python

    Author = g.ObjectType("Author", fields=(
        g.field("name", type=g.String),
    ))

    Root = g.ObjectType("Root", fields=(
        g.field("author_count", type=g.Int),
        g.field("authors", type=g.ListType(Author)),

        g.field("book_count", type=g.Int),
        g.field("books", type=g.ListType(Book), params=(
            g.param("genre", type=g.String, default=None),
        )),
    ))

We define an ``AuthorQuery``,
which can be resolved by a new resolver.



.. code-block:: python

    class AuthorQuery(object):
        def __init__(self, object_query):
            self.type = (AuthorQuery, object_query.type)
            self.object_query = object_query

    @g.resolver((AuthorQuery, Author))
    def resolve_authors(graph, query):
        authors = session.query(AuthorRecord.name).all()

        def resolve_field(author, field):
            if field == Author.fields.name:
                return author.name
            else:
                raise Exception("unknown field: {}".format(field))

        return [
            query.object_query.create_object(dict(
                (field_query.key, resolve_field(author, field_query.field))
                for field_query in query.object_query.field_queries
            ))
            for author in authors
        ]

    resolvers = (resolve_root, resolve_authors, resolve_books)

Finally, we update the root resolver to resolve the ``authors`` field.


.. code-block:: python

    @g.resolver(Root)
    def resolve_root(graph, query):
        def resolve_field(field_query):
            if field_query.field == Root.fields.author_count:
                return session.query(AuthorRecord).count()
            elif field_query.field == Root.fields.authors:
                return graph.resolve(AuthorQuery(field_query.type_query.element_query))
            elif field_query.field == Root.fields.book_count:
                return session.query(BookRecord).count()

Adding an author field to books
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As the last change to the schema,
let's add an ``author`` field to ``Book``.
We start by updating the type:


.. code-block:: python

    Book = g.ObjectType("Book", fields=(
        g.field("title", type=g.String),
        g.field("genre", type=g.String),
        g.field("author", type=Author),
    ))

We then need to update the resolver for books.
If the ``author`` field is requested,
then we'll need to fetch the ``author_id`` from the database,
so we update ``field_to_expression``:


.. code-block:: python

    field_to_expression = {
        Book.fields.title: BookRecord.title,
        Book.fields.genre: BookRecord.genre,
        Book.fields.author: BookRecord.author_id,
    }

As well as fetching books,
we'll need to fetch the authors too.
We can do this by delegating to the graph.
When fetching authors for the root, having them returned as a list was the most convenient format.
However, when fetching authors for books,
it'd be more convenient to return them in a dictionary keyed by ID so they can easily matched to books by ``author_id``.
We can change the ``AuthorQuery`` to optionally allow this alternative format:


.. code-block:: python

    class AuthorQuery(object):
        def __init__(self, object_query, is_keyed_by_id=False):
            self.type = (AuthorQuery, object_query.type)
            self.object_query = object_query
            self.is_keyed_by_id = is_keyed_by_id

        def key_by_id(self):
            return AuthorQuery(self.object_query, is_keyed_by_id=True)

We then need to update the resolver to handle this:


.. code-block:: python

    @g.resolver((AuthorQuery, Author))
    def resolve_authors(graph, query):
        sqlalchemy_query = session.query(AuthorRecord.name)

        if query.is_keyed_by_id:
            sqlalchemy_query = sqlalchemy_query.add_columns(AuthorRecord.id)

        authors = sqlalchemy_query.all()

        def resolve_field(author, field):
            if field == Author.fields.name:
                return author.name
            else:
                raise Exception("unknown field: {}".format(field))

        def to_object(author):
            return query.object_query.create_object(dict(
                (field_query.key, resolve_field(author, field_query.field))
                for field_query in query.object_query.field_queries
            ))

        if query.is_keyed_by_id:
            return dict(
                (author.id, to_object(author))
                for author in authors
            )
        else:
            return [
                to_object(author)
                for author in authors
            ]

Now we can update the books resolver to fetch the authors using the graph:


.. code-block:: python

    books = sqlalchemy_query.all()

    authors = dict(
        (field_query.key, graph.resolve(AuthorQuery(field_query.type_query).key_by_id()))
        for field_query in query.object_query.field_queries
        if field_query.field == Book.fields.author
    )

This creates a dictionary mapping from each field query to the authors fetched for that field query.
We can this use this dictionary when resolving each field:


.. code-block:: python

    def resolve_field(book, field_query):
        if field_query.field == Book.fields.title:
            return book.title
        elif field_query.field == Book.fields.genre:
            return book.genre
        elif field_query.field == Book.fields.author:
            return authors[field_query.key][book.author_id]
        else:
            raise Exception("unknown field: {}".format(field_query.field))

    return [
        query.object_query.create_object(dict(
            (field_query.key, resolve_field(book, field_query))
            for field_query in query.object_query.field_queries
        ))
        for book in books
    ]

Now if we update our executed query:


.. code-block:: python

    print("result:", execute(
        """
            query {
                books(genre: "comedy") {
                    title
                    author {
                        name
                    }
                }
            }
        """,
        graph=graph,
        query_type=Root,
    ))

We should see:

::

    result: {'books': [{'title': 'Leave It to Psmith', 'author': {'name': 'PG Wodehouse'}}, {'title': 'Right Ho, Jeeves', 'author': {'name': 'PG Wodehouse'}}]}

One inefficiency in the current implementation is that we fetch all authors,
regardless of whether they're the author of a book that we've fetched.
We can fix this by filtering the author query by IDs,
similarly to how we filtered the book query by genre.
We update ``AuthorQuery`` to add in an ``ids`` attribute:


.. code-block:: python

    class AuthorQuery(object):
        def __init__(self, object_query, ids=None, is_keyed_by_id=False):
            self.type = (AuthorQuery, object_query.type)
            self.object_query = object_query
            self.ids = ids
            self.is_keyed_by_id = is_keyed_by_id

        def key_by_id(self):
            return AuthorQuery(self.object_query, ids=self.ids, is_keyed_by_id=True)

        def where(self, *, ids):
            return AuthorQuery(self.object_query, ids=ids, is_keyed_by_id=self.is_keyed_by_id)

We use that ``ids`` attribute in the author resolver:


.. code-block:: python

    sqlalchemy_query = session.query(AuthorRecord.name)

    if query.ids is not None:
        sqlalchemy_query = sqlalchemy_query.filter(AuthorRecord.id.in_(query.ids))

    if query.is_keyed_by_id:
        sqlalchemy_query = sqlalchemy_query.add_columns(AuthorRecord.id)

    authors = sqlalchemy_query.all()

And we set the IDs in the book resolver:


.. code-block:: python

    books = sqlalchemy_query.all()

    def get_author_ids():
        return frozenset(
            book.author_id
            for book in books
        )

    def get_authors_for_field_query(field_query):
        author_query = AuthorQuery(field_query.type_query) \
            .where(ids=get_author_ids()) \
            .key_by_id()
        return graph.resolve(author_query)

    authors = dict(
        (field_query.key, get_authors_for_field_query(field_query))
        for field_query in query.object_query.field_queries
        if field_query.field == Book.fields.author
    )

Dependency injection
~~~~~~~~~~~~~~~~~~~~

In our example so far,
we've treated the SQLAlchemy session as a global variable.
In practice, it's sometimes useful to pass the session (and other dependencies) around explicitly.
Dependencies for resolvers are marked using the decorator ``g.dependencies``,
which allow dependencies to be passed as keyword arguments to resolvers.
For instance, to add a dependency on a SQLAlchemy session to ``resolve_root``:


.. code-block:: python

    @g.resolver(Root)
    @g.dependencies(session=sqlalchemy.orm.Session)
    def resolve_root(graph, query, *, session):

A dependency can be identified by any value.
In this case, we identify the session dependency by its class, ``sqlalchemy.orm.Session``.
When creating the graph,
we need to pass in dependencies:


.. code-block:: python

    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })


Extracting duplication
~~~~~~~~~~~~~~~~~~~~~~

When implementing resolvers, there are common patterns that tend to occur.
By extracting these common patterns into functions that build resolvers,
we can reduce duplication and simplify the definition of resolvers.
For instance, our root resolver can be rewritten as:


.. code-block:: python

    resolve_root = g.root_object_resolver(Root)

    @resolve_root.field(Root.fields.author_count)
    @g.dependencies(session=sqlalchemy.orm.Session)
    def root_resolve_author_count(graph, query, args, *, session):
        return session.query(AuthorRecord).count()

    @resolve_root.field(Root.fields.authors)
    def root_resolve_authors(graph, query, args):
        return graph.resolve(AuthorQuery(query.element_query))

    @resolve_root.field(Root.fields.book_count)
    @g.dependencies(session=sqlalchemy.orm.Session)
    def root_resolve_book_count(graph, query, args, *, session):
        return session.query(BookRecord).count()

    @resolve_root.field(Root.fields.books)
    def root_resolve_books(graph, query, args):
        book_query = BookQuery(query.element_query)

        if args.genre is not None:
            book_query = book_query.where(genre=args.genre)

        return graph.resolve(book_query)

Similarly, we can use the ``graphlayer.sqlalchemy`` module to define the resolvers for authors and books:


.. code-block:: python

    import graphlayer.sqlalchemy as gsql

    @resolve_root.field(Root.fields.authors)
    def root_resolve_authors(graph, query, args):
        return graph.resolve(gsql.select(query))

    @resolve_root.field(Root.fields.books)
    def root_resolve_books(graph, query, args):
        book_query = gsql.select(query)

        if args.genre is not None:
            book_query = book_query.where(BookRecord.genre == args.genre)

        return graph.resolve(book_query)

    resolve_authors = gsql.sql_table_resolver(
        Author,
        AuthorRecord,
        fields={
            Author.fields.name: gsql.expression(AuthorRecord.name),
        },
    )

    resolve_books = gsql.sql_table_resolver(
        Book,
        BookRecord,
        fields={
            Book.fields.title: gsql.expression(BookRecord.title),
            Book.fields.genre: gsql.expression(BookRecord.genre),
            Book.fields.author: lambda graph, field_query: gsql.join(
                key=BookRecord.author_id,
                resolve=lambda author_ids: graph.resolve(
                    gsql.select(field_query.type_query).by(AuthorRecord.id, author_ids),
                ),
            ),
        },
    )


