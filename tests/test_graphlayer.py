from precisely import assert_that, contains_exactly, has_attrs

import graphlayer as g
from graphlayer import iterables


def test_can_get_scalar_from_root():
    Root = g.ObjectType(
        "Root",
        fields=[
            g.field("one", type=g.IntType),
            g.field("two", type=g.IntType),
        ],
    )
    
    @g.expander(Root, g.object_representation)
    def expand_root(graph, query):
        values = dict(
            one=1,
            two=2,
        )
        
        return g.ObjectResult(iterables.to_dict(
            (key, values[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    expanders = [expand_root]
    execute = g.executor(expanders)
    
    query = Root(
        value=Root.one(),
    )
    result = execute(query, g.object_representation)
    
    assert_that(result, has_attrs(value=1))


def test_constant_object_expander():
    Root = g.ObjectType(
        "Root",
        fields=[
            g.field("one", type=g.IntType),
            g.field("two", type=g.IntType),
        ],
    )
    
    expand_root = g.constant_object_expander(Root, dict(one=1, two=2))
    
    expanders = [expand_root]
    execute = g.executor(expanders)
    
    query = Root(
        value=Root.one(),
    )
    result = execute(query, g.object_representation)
    
    assert_that(result, has_attrs(value=1))


def test_can_recursively_expand():
    Root = g.ObjectType(
        "Root",
        fields=lambda: [
            g.field("books", type=g.ListType(Book)),
        ],
    )
    
    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.StringType),
        ],
    )
    
    @g.expander(Root, g.object_representation)
    def expand_root(graph, query):
        def resolve_field(query):
            return graph.expand(query, g.object_representation)
        
        return g.ObjectResult(iterables.to_dict(
            (key, resolve_field(field_query.query))
            for key, field_query in query.fields.items()
        ))
    
    @g.expander(g.ListType(Book), g.object_representation)
    def expand_book(graph, query):
        books = [
            dict(title="Leave it to Psmith"),
            dict(title="Pericles, Prince of Tyre"),
        ]
        return [
            g.ObjectResult(iterables.to_dict(
                (key, book[field_query.field.name])
                for key, field_query in query.element_query.fields.items()
            ))
            for book in books
        ]
    
    expanders = [expand_root, expand_book]
    execute = g.executor(expanders)
    
    query = Root(
        books=Root.books(
            title=Book.title(),
        ),
    )
    result = execute(query, g.object_representation)
    
    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(title="Leave it to Psmith"),
            has_attrs(title="Pericles, Prince of Tyre"),
        ),
    ))


def test_can_recursively_expand_selected_fields():
    Root = g.ObjectType(
        "Root",
        fields=lambda: [
            g.field("books", type=g.ListType(Book)),
        ],
    )
    
    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("author", type=Author),
            g.field("title", type=g.StringType),
        ],
    )
    
    Author = g.ObjectType(
        "Author",
        fields=lambda: [
            g.field("name", type=g.StringType),
        ],
    )
    
    @g.expander(Root, g.object_representation)
    def expand_root(graph, query):
        def resolve_field(query):
            return graph.expand(query, g.object_representation)
        
        return g.ObjectResult(iterables.to_dict(
            (key, resolve_field(field_query.query))
            for key, field_query in query.fields.items()
        ))
    
    books = [
        dict(author_id="wodehouse", title="Leave it to Psmith"),
        dict(author_id="shakespeare", title="Pericles, Prince of Tyre"),
    ]
    
    def resolve_title(graph, book, query):
        return book["title"]
    
    def resolve_author(graph, book, query):
        return graph.expand(
            query,
            g.object_representation,
            representations={
                "author_id": book["author_id"],
            },
        )
    
    fields = {
        "title": resolve_title,
        "author": resolve_author,
    }

    def resolve_field(graph, book, field_query):
        return fields[field_query.field.name](graph, book, field_query.query)
    
    @g.expander(g.ListType(Book), g.object_representation)
    def expand_book(graph, query):
        return [
            g.ObjectResult(iterables.to_dict(
                (key, resolve_field(graph, book, field_query))
                for key, field_query in query.element_query.fields.items()
            ))
            for book in books
        ]
    
    authors = {
        "wodehouse": dict(name="PG Wodehouse"),
        "shakespeare": dict(name="William Shakespeare"),
    }
    
    @g.expander(Author, g.object_representation, dict(author_id="author_id"))
    def expand_author(graph, query, author_id):
        author = authors[author_id]
        return g.ObjectResult(iterables.to_dict(
            (key, author[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    expanders = [expand_root, expand_book, expand_author]
    execute = g.executor(expanders)
    
    query = Root(
        books=Root.books(
            author=Book.author(
                name=Author.name(),
            ),
            title=Book.title(),
        ),
    )
    result = execute(query, g.object_representation)
    
    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(
                author=has_attrs(name="PG Wodehouse"),
                title="Leave it to Psmith",
            ),
            has_attrs(
                author=has_attrs(name="William Shakespeare"),
                title="Pericles, Prince of Tyre",
            ),
        ),
    ))
