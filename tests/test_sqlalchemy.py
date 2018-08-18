from __future__ import unicode_literals

from precisely import assert_that, contains_exactly, has_attrs
import sqlalchemy.ext.declarative
import sqlalchemy.orm

import graphlayer as g
from graphlayer.expanders import root_object_expander
from graphlayer.sqlalchemy import sql_table_expander


Base = sqlalchemy.ext.declarative.declarative_base()


def test_can_recursively_expand_selected_fields():
    class AuthorRow(Base):
        __tablename__ = "author"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_name = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
        c_author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(AuthorRow.c_id))
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    session.add(AuthorRow(c_id=1, c_name="PG Wodehouse"))
    session.add(AuthorRow(c_id=2, c_name="William Shakespeare"))
    session.add(BookRow(c_title="Leave it to Psmith", c_author_id=1))
    session.add(BookRow(c_title="Pericles, Prince of Tyre", c_author_id=2))

    session.commit()
    
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
    
    expand_root = root_object_expander(Root, {
        Root.books: {
            "where": None,
        },
    })
    
    expand_book = sql_table_expander(
        Book,
        BookRow,
        expressions={
            Book.title: BookRow.c_title,
        },
        joins={
            Book.author: {
                BookRow.c_author_id: AuthorRow.c_id,
            },
        },
        session=session,
    )
    
    expand_author = sql_table_expander(
        Author,
        AuthorRow,
        expressions={
            Author.name: AuthorRow.c_name,
        },
        session=session,
    )
    expanders = [expand_root, expand_book, expand_author]
    
    query = Root(
        books=Root.books(
            author=Book.author(
                name=Author.name(),
            ),
            title=Book.title(),
        ),
    )
    result = g.create_graph(expanders).expand(Root, g.object_representation, {g.object_query: query})
    
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
