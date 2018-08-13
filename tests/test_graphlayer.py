from precisely import assert_that, contains_exactly, has_attrs

import graphlayer as g
from graphlayer import iterables


def test_can_get_scalar_from_root():
    Root = g.ObjectType(
        "Root",
        fields=[
            g.field("one", type=g.Int),
            g.field("two", type=g.Int),
        ],
    )
    
    @g.expander(Root, g.ObjectResult)
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
    
    result = execute(Root(
        value=Root.one(),
    ))
    
    assert_that(result, has_attrs(value=1))


def test_constant_object_expander():
    Root = g.ObjectType(
        "Root",
        fields=[
            g.field("one", type=g.Int),
            g.field("two", type=g.Int),
        ],
    )
    
    expand_root = g.constant_object_expander(Root, dict(one=1, two=2))
    
    expanders = [expand_root]
    execute = g.executor(expanders)
    
    result = execute(Root(
        value=Root.one(),
    ))
    
    assert_that(result, has_attrs(value=1))


def test_can_recursively_expand():
    Root = g.ObjectType(
        "Root",
        fields=lambda: [
            g.field("books", type=g.List(Book)),
        ],
    )
    
    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )
    
    @g.expander(Root, g.ObjectResult)
    def expand_root(graph, query):
        def resolve_field(query):
            return graph.expand(query, g.ListResult(g.ObjectResult))
        
        return g.ObjectResult(iterables.to_dict(
            (key, resolve_field(field_query.query))
            for key, field_query in query.fields.items()
        ))
    
    @g.expander(g.List(Book), g.ListResult(g.ObjectResult))
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
    
    result = execute(Root(
        books=Root.books(
            title=Book.title(),
        ),
    ))
    
    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(title="Leave it to Psmith"),
            has_attrs(title="Pericles, Prince of Tyre"),
        ),
    ))
