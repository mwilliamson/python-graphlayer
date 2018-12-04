from __future__ import unicode_literals

from precisely import assert_that, contains_exactly, has_attrs
import sqlalchemy.ext.declarative
import sqlalchemy.orm

import graphlayer as g
from graphlayer import sqlalchemy as gsql
from graphlayer.expanders import root_object_expander


def test_can_get_fields_backed_by_expressions():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.add(BookRow(c_title="Pericles, Prince of Tyre"))
    session.commit()
    
    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.StringType),
        ],
    )
    
    expand_book = gsql.sql_table_expander(
        Book,
        BookRow,
        fields={
            Book.title: gsql.expression(BookRow.c_title),
        },
        session=session,
    )
    
    expanders = [expand_book]
    
    query = gsql.select(g.ListType(Book)(
        title=Book.title(),
    ))
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, contains_exactly(
        has_attrs(
            title="Leave it to Psmith",
        ),
        has_attrs(
            title="Pericles, Prince of Tyre",
        ),
    ))


def test_can_pass_arguments_to_expression():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_title="Leave it to Psmith"))
    session.commit()
    
    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.StringType, args=[
                g.param("truncate", g.IntType),
            ]),
        ],
    )
    
    expand_book = gsql.sql_table_expander(
        Book,
        BookRow,
        fields={
            Book.title: lambda args: gsql.expression(sqlalchemy.func.substr(BookRow.c_title, 1, args.truncate)),
        },
        session=session,
    )
    
    expanders = [expand_book]
    
    query = gsql.select(g.ListType(Book)(
        title=Book.title(Book.title.truncate(8)),
    ))
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, contains_exactly(
        has_attrs(
            title="Leave it",
        ),
    ))


def test_can_pass_arguments_from_root():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class BookRow(Base):
        __tablename__ = "book"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    session.add(BookRow(c_id=1, c_title="Leave it to Psmith"))
    session.add(BookRow(c_id=2, c_title="Pericles, Prince of Tyre"))

    session.commit()
    
    Root = g.ObjectType(
        "Root",
        fields=lambda: [
            g.field("books", type=g.ListType(Book), args=[
                g.param("id", g.IntType),
            ]),
        ],
    )
    
    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.StringType),
        ],
    )
    
    expand_root = root_object_expander(Root)
    
    @expand_root.field(Root.books)
    def root_books_args(graph, query, args):
        return graph.expand(expand_book.select(query).where(expand_book.id(args.id)))
    
    expand_book = gsql.sql_table_expander(
        Book,
        BookRow,
        fields={
            Book.title: gsql.expression(BookRow.c_title),
        },
        session=session,
    )
    
    @expand_book.add("id")
    def expand_book_id(id):
        return BookRow.c_id == id
    
    expanders = [expand_root, expand_book]
    
    query = Root(
        books=Root.books(
            Root.books.id(1),
            
            title=Book.title(),
        ),
    )
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(
                title="Leave it to Psmith",
            ),
        ),
    ))


def test_can_recursively_expand_selected_fields():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
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
    
    expand_root = root_object_expander(Root)
    
    @expand_root.field(Root.books)
    def expand_root_field_books(graph, query, args):
        return graph.expand(expand_book.select(query))
    
    expand_book = gsql.sql_table_expander(
        Book,
        BookRow,
        fields={
            Book.title: gsql.expression(BookRow.c_title),
            Book.author: gsql.single(gsql.sql_join({
                BookRow.c_author_id: AuthorRow.c_id,
            })),
        },
        session=session,
    )
    
    expand_author = gsql.sql_table_expander(
        Author,
        AuthorRow,
        fields={
            Author.name: gsql.expression(AuthorRow.c_name),
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
    result = g.create_graph(expanders).expand(query)
    
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


def test_can_resolve_many_to_one_field():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
        
    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    session.add(LeftRow(c_id=1, c_value="one"))
    session.add(RightRow(c_id=1, c_value="two"))
    session.add(LeftRow(c_id=2, c_value="three"))
    session.add(RightRow(c_id=2, c_value="four"))
    session.commit()
    
    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.StringType),
            g.field("right", type=Right),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.StringType),
        ],
    )
    
    expand_left = gsql.sql_table_expander(
        Left,
        LeftRow,
        fields={
            Left.value: gsql.expression(LeftRow.c_value),
            Left.right: gsql.single(gsql.sql_join({
                LeftRow.c_id: RightRow.c_id,
            })),
        },
        session=session,
    )
    
    expand_right = gsql.sql_table_expander(
        Right,
        RightRow,
        fields={
            Right.value: gsql.expression(RightRow.c_value),
        },
        session=session,
    )
    
    expanders = [expand_left, expand_right]
    
    query = gsql.select(g.ListType(Left)(
        value=Left.value(),
        right=Left.right(
            value=Right.value(),
        ),
    ))
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, contains_exactly(
        has_attrs(
            value="one",
            right=has_attrs(
                value="two",
            ),
        ),
        has_attrs(
            value="three",
            right=has_attrs(
                value="four",
            ),
        ),
    ))


def test_can_resolve_many_to_one_or_zero_field():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
        
    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    session.add(LeftRow(c_id=1, c_value="one"))
    session.add(RightRow(c_id=1, c_value="two"))
    session.add(LeftRow(c_id=2, c_value="three"))
    session.commit()
    
    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.StringType),
            g.field("right", type=g.NullableType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.StringType),
        ],
    )
    
    expand_left = gsql.sql_table_expander(
        Left,
        LeftRow,
        fields={
            Left.value: gsql.expression(LeftRow.c_value),
            Left.right: gsql.single_or_null(gsql.sql_join({
                LeftRow.c_id: RightRow.c_id,
            })),
        },
        session=session,
    )
    
    expand_right = gsql.sql_table_expander(
        Right,
        RightRow,
        fields={
            Right.value: gsql.expression(RightRow.c_value),
        },
        session=session,
    )
    
    expanders = [expand_left, expand_right]
    
    query = gsql.select(g.ListType(Left)(
        value=Left.value(),
        right=Left.right(
            value=Right.value(),
        ),
    ))
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, contains_exactly(
        has_attrs(
            value="one",
            right=has_attrs(
                value="two",
            ),
        ),
        has_attrs(
            value="three",
            right=None,
        ),
    ))


def test_can_resolve_one_to_many_field():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
        
    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey(LeftRow.c_id))
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    
    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_left_id=1, c_value="right 1a"))
    session.add(RightRow(c_left_id=1, c_value="right 1b"))
    
    session.add(LeftRow(c_id=2, c_value="left 2"))
    
    session.add(LeftRow(c_id=3, c_value="left 3"))
    session.add(RightRow(c_left_id=3, c_value="right 3"))
    session.commit()
    
    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.StringType),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.StringType),
        ],
    )
    
    expand_left = gsql.sql_table_expander(
        Left,
        LeftRow,
        fields={
            Left.value: gsql.expression(LeftRow.c_value),
            Left.rights: gsql.many(gsql.sql_join({
                LeftRow.c_id: RightRow.c_left_id,
            })),
        },
        session=session,
    )
    
    expand_right = gsql.sql_table_expander(
        Right,
        RightRow,
        fields={
            Right.value: gsql.expression(RightRow.c_value),
        },
        session=session,
    )
    
    expanders = [expand_left, expand_right]
    
    query = gsql.select(g.ListType(Left)(
        value=Left.value(),
        rights=Left.rights(
            value=Right.value(),
        ),
    ))
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            rights=contains_exactly(
                has_attrs(value="right 1a"),
                has_attrs(value="right 1b"),
            ),
        ),
        has_attrs(
            value="left 2",
            rights=contains_exactly(),
        ),
        has_attrs(
            value="left 3",
            rights=contains_exactly(
                has_attrs(value="right 3"),
            ),
        ),
    ))


def test_can_resolve_join_through_association_table():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class LeftRow(Base):
        __tablename__ = "left"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
    
    class AssociationRow(Base):
        __tablename__ = "association"
        
        c_left_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_right_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    
    class RightRow(Base):
        __tablename__ = "right"

        c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    
    session.add(LeftRow(c_id=1, c_value="left 1"))
    session.add(RightRow(c_id=101, c_value="right 1a"))
    session.add(RightRow(c_id=102, c_value="right 1b"))
    session.add(AssociationRow(c_left_id=1, c_right_id=101))
    session.add(AssociationRow(c_left_id=1, c_right_id=102))
    
    session.add(LeftRow(c_id=2, c_value="left 2"))
    
    session.add(LeftRow(c_id=3, c_value="left 3"))
    session.add(RightRow(c_id=103, c_value="right 3"))
    session.add(AssociationRow(c_left_id=3, c_right_id=103))
    
    session.commit()
    
    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.StringType),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.StringType),
        ],
    )
    
    expand_left = gsql.sql_table_expander(
        Left,
        LeftRow,
        fields={
            Left.value: gsql.expression(LeftRow.c_value),
            Left.rights: gsql.many(gsql.sql_join(
                {LeftRow.c_id: AssociationRow.c_left_id},
                AssociationRow,
                {AssociationRow.c_right_id: RightRow.c_id},
            )),
        },
        session=session,
    )
    
    expand_right = gsql.sql_table_expander(
        Right,
        RightRow,
        fields={
            Right.value: gsql.expression(RightRow.c_value),
        },
        session=session,
    )
    
    expanders = [expand_left, expand_right]
    
    query = gsql.select(g.ListType(Left)(
        value=Left.value(),
        rights=Left.rights(
            value=Right.value(),
        ),
    ))
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, contains_exactly(
        has_attrs(
            value="left 1",
            rights=contains_exactly(
                has_attrs(value="right 1a"),
                has_attrs(value="right 1b"),
            ),
        ),
        has_attrs(
            value="left 2",
            rights=contains_exactly(),
        ),
        has_attrs(
            value="left 3",
            rights=contains_exactly(
                has_attrs(value="right 3"),
            ),
        ),
    ))


def test_can_join_tables_using_multi_column_key():
    Base = sqlalchemy.ext.declarative.declarative_base()
    
    class LeftRow(Base):
        __tablename__ = "left"

        c_id_1 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_id_2 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
        
    class RightRow(Base):
        __tablename__ = "right"

        c_id_1 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_id_2 = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        c_value = sqlalchemy.Column(sqlalchemy.Unicode)
    
    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    
    session = sqlalchemy.orm.Session(engine)
    session.add(LeftRow(c_id_1=1, c_id_2=2, c_value="one"))
    session.add(RightRow(c_id_1=1, c_id_2=2, c_value="two"))
    session.add(LeftRow(c_id_1=1, c_id_2=3, c_value="three"))
    session.add(RightRow(c_id_1=1, c_id_2=3, c_value="four"))
    session.commit()
    
    Left = g.ObjectType(
        "Left",
        fields=lambda: [
            g.field("value", type=g.StringType),
            g.field("right", type=Right),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.StringType),
        ],
    )
    
    expand_left = gsql.sql_table_expander(
        Left,
        LeftRow,
        fields={
            Left.value: gsql.expression(LeftRow.c_value),
            Left.right: gsql.single(gsql.sql_join({
                LeftRow.c_id_1: RightRow.c_id_1,
                LeftRow.c_id_2: RightRow.c_id_2,
            })),
        },
        session=session,
    )
    
    expand_right = gsql.sql_table_expander(
        Right,
        RightRow,
        fields={
            Right.value: gsql.expression(RightRow.c_value),
        },
        session=session,
    )
    
    expanders = [expand_left, expand_right]
    
    query = gsql.select(g.ListType(Left)(
        value=Left.value(),
        right=Left.right(
            value=Right.value(),
        ),
    ))
    result = g.create_graph(expanders).expand(query)
    
    assert_that(result, contains_exactly(
        has_attrs(
            value="one",
            right=has_attrs(
                value="two",
            ),
        ),
        has_attrs(
            value="three",
            right=has_attrs(
                value="four",
            ),
        ),
    ))
