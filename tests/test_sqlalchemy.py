from __future__ import unicode_literals

from precisely import assert_that, contains_exactly, equal_to, has_attrs
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import pytest

import graphlayer as g
from graphlayer import sqlalchemy as gsql
from graphlayer.resolvers import root_object_resolver


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
            g.field("title", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("title", Book.fields.title()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(
            title="Leave it to Psmith",
        ),
        has_attrs(
            title="Pericles, Prince of Tyre",
        ),
    ))


class TestReturnShapeMatchesQueryShape(object):
    @pytest.fixture(autouse=True)
    def setup(self):
        Base = sqlalchemy.ext.declarative.declarative_base()

        class BookRow(Base):
            __tablename__ = "book"

            c_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
            c_title = sqlalchemy.Column(sqlalchemy.Unicode, nullable=False)

        engine = sqlalchemy.create_engine("sqlite:///:memory:")

        Base.metadata.create_all(engine)

        session = sqlalchemy.orm.Session(engine)

        Book = g.ObjectType(
            "Book",
            fields=lambda: [
                g.field("title", type=g.String),
            ],
        )

        book_resolver = gsql.sql_table_resolver(
            Book,
            BookRow,
            fields={
                Book.fields.title: gsql.expression(BookRow.c_title),
            },
        )

        resolvers = [book_resolver]

        graph_definition = g.define_graph(resolvers)
        self.graph = graph_definition.create_graph({
            sqlalchemy.orm.Session: session,
        })
        self.Book = Book
        self.BookRow = BookRow
        self.session = session

    def test_given_there_are_no_rows_then_requesting_list_returns_empty_list(self):
        query = gsql.select(g.ListType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, contains_exactly())

    def test_given_there_are_rows_then_requesting_list_returns_list(self):
        self.add_books("Leave it to Psmith", "Pericles, Prince of Tyre")

        query = gsql.select(g.ListType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, contains_exactly(
            has_attrs(
                title="Leave it to Psmith",
            ),
            has_attrs(
                title="Pericles, Prince of Tyre",
            ),
        ))

    def test_given_there_are_no_rows_then_requesting_nullable_returns_null(self):
        query = gsql.select(g.NullableType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, equal_to(None))

    def test_given_there_is_one_row_then_requesting_nullable_returns_object(self):
        self.add_books("Leave it to Psmith")

        query = gsql.select(g.NullableType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, has_attrs(title="Leave it to Psmith"))

    def test_given_there_is_more_than_one_row_then_requesting_nullable_raises_error(self):
        self.add_books("Leave it to Psmith", "Pericles, Prince of Tyre")

        query = gsql.select(g.NullableType(self.Book)(
            g.key("title", self.Book.fields.title()),
        ))
        error = pytest.raises(ValueError, lambda: self.resolve(query))

        assert_that(str(error.value), equal_to("expected exactly zero or one values"))

    def test_given_there_are_no_rows_then_requesting_object_raises_error(self):
        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        ))
        error = pytest.raises(ValueError, lambda: self.resolve(query))

        assert_that(str(error.value), equal_to("expected exactly one value"))

    def test_given_there_is_one_row_then_requesting_object_returns_object(self):
        self.add_books("Leave it to Psmith")

        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        ))
        result = self.resolve(query)

        assert_that(result, has_attrs(title="Leave it to Psmith"))

    def test_given_there_is_more_than_one_row_then_requesting_object_raises_error(self):
        self.add_books("Leave it to Psmith", "Pericles, Prince of Tyre")

        query = gsql.select(self.Book(
            g.key("title", self.Book.fields.title()),
        ))
        error = pytest.raises(ValueError, lambda: self.resolve(query))

        assert_that(str(error.value), equal_to("expected exactly one value"))

    def add_books(self, *titles):
        for title in titles:
            self.session.add(self.BookRow(c_title=title))
        self.session.commit()

    def resolve(self, query):
        return self.graph.resolve(query)


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
            g.field("title", type=g.String, params=[
                g.param("truncate", g.Int),
            ]),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: lambda args: gsql.expression(sqlalchemy.func.substr(BookRow.c_title, 1, args.truncate)),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("title", Book.fields.title(Book.fields.title.params.truncate(8))),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

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
            g.field("books", type=g.ListType(Book), params=[
                g.param("id", g.Int),
            ]),
        ],
    )

    Book = g.ObjectType(
        "Book",
        fields=lambda: [
            g.field("title", type=g.String),
        ],
    )

    resolve_root = root_object_resolver(Root)

    @resolve_root.field(Root.fields.books)
    def root_books_args(graph, query, args):
        return graph.resolve(BookQuery.select(query).where(BookQuery.id(args.id)))

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
        },
    )

    class BookQuery(object):
        select = gsql.select

        @staticmethod
        def id(id):
            return BookRow.c_id == id

    resolvers = [resolve_root, book_resolver]

    query = Root(
        g.key("books", Root.fields.books(
            Root.fields.books.params.id(1),

            g.key("title", Book.fields.title()),
        )),
    )

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

    assert_that(result, has_attrs(
        books=contains_exactly(
            has_attrs(
                title="Leave it to Psmith",
            ),
        ),
    ))


def test_can_recursively_resolve_selected_fields():
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
            g.field("title", type=g.String),
        ],
    )

    Author = g.ObjectType(
        "Author",
        fields=lambda: [
            g.field("name", type=g.String),
        ],
    )

    resolve_root = root_object_resolver(Root)

    @resolve_root.field(Root.fields.books)
    def resolve_root_field_books(graph, query, args):
        return graph.resolve(gsql.select(query))

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.title: gsql.expression(BookRow.c_title),
            Book.fields.author: gsql.sql_join({
                BookRow.c_author_id: AuthorRow.c_id,
            }),
        },
    )

    author_resolver = gsql.sql_table_resolver(
        Author,
        AuthorRow,
        fields={
            Author.fields.name: gsql.expression(AuthorRow.c_name),
        },
    )
    resolvers = [resolve_root, book_resolver, author_resolver]

    query = Root(
        g.key("books", Root.fields.books(
            g.key("author", Book.fields.author(
                g.key("name", Author.fields.name()),
            )),
            g.key("title", Book.fields.title()),
        )),
    )

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

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
            g.field("value", type=g.String),
            g.field("right", type=Right),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: gsql.sql_join({
                LeftRow.c_id: RightRow.c_id,
            }),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

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
            g.field("value", type=g.String),
            g.field("right", type=g.NullableType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: gsql.sql_join({
                LeftRow.c_id: RightRow.c_id,
            }),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

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
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: gsql.sql_join({
                LeftRow.c_id: RightRow.c_left_id,
            }),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

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
            g.field("value", type=g.String),
            g.field("rights", type=g.ListType(Right)),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.rights: gsql.sql_join(
                {LeftRow.c_id: AssociationRow.c_left_id},
                AssociationRow,
                {AssociationRow.c_right_id: RightRow.c_id},
            ),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("rights", Left.fields.rights(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

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
            g.field("value", type=g.String),
            g.field("right", type=Right),
        ],
    )
    Right = g.ObjectType(
        "Right",
        fields=lambda: [
            g.field("value", type=g.String),
        ],
    )

    left_resolver = gsql.sql_table_resolver(
        Left,
        LeftRow,
        fields={
            Left.fields.value: gsql.expression(LeftRow.c_value),
            Left.fields.right: gsql.sql_join({
                LeftRow.c_id_1: RightRow.c_id_1,
                LeftRow.c_id_2: RightRow.c_id_2,
            }),
        },
    )

    right_resolver = gsql.sql_table_resolver(
        Right,
        RightRow,
        fields={
            Right.fields.value: gsql.expression(RightRow.c_value),
        },
    )

    resolvers = [left_resolver, right_resolver]

    query = gsql.select(g.ListType(Left)(
        g.key("value", Left.fields.value()),
        g.key("right", Left.fields.right(
            g.key("value", Right.fields.value()),
        )),
    ))

    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({sqlalchemy.orm.Session: session})
    result = graph.resolve(query)

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


def test_can_map_values_from_sql_expression():
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
            g.field("initial", type=g.String),
        ],
    )

    book_resolver = gsql.sql_table_resolver(
        Book,
        BookRow,
        fields={
            Book.fields.initial: gsql.expression(BookRow.c_title).map_value(lambda title: title[0]),
        },
    )

    resolvers = [book_resolver]

    query = gsql.select(g.ListType(Book)(
        g.key("initial", Book.fields.initial()),
    ))
    graph_definition = g.define_graph(resolvers)
    graph = graph_definition.create_graph({
        sqlalchemy.orm.Session: session,
    })
    result = graph.resolve(query)

    assert_that(result, contains_exactly(
        has_attrs(initial="L"),
        has_attrs(initial="P"),
    ))
