import enum
import textwrap

from precisely import assert_that, contains_exactly, equal_to, has_attrs, includes
import pytest

from graphlayer import GraphError, schema
from .matchers import is_query


def test_when_param_does_not_exist_on_params_then_error_is_raised():
    params = schema.Params("book", {})

    error = pytest.raises(GraphError, lambda: params.author)

    assert_that(str(error.value), equal_to("book has no param author"))


def test_params_are_accessible_with_trailing_underscore():
    params = schema.Params("book", (
        schema.param("class", type=schema.String),
    ))
    assert_that(params.class_, equal_to(getattr(params, "class")))


def test_fields_are_accessible_with_trailing_underscore():
    fields = schema.Fields("Book", (
        schema.field("class", type=schema.String),
    ))
    assert_that(fields.class_, equal_to(getattr(fields, "class")))


def test_when_field_does_not_exist_on_object_type_then_error_is_raised():
    book = schema.ObjectType("Book", fields=(
        schema.field("title", schema.String),
    ))

    error = pytest.raises(GraphError, lambda: book.fields.author)

    assert_that(str(error.value), equal_to("Book has no field author"))


def test_given_input_field_has_default_when_input_field_is_not_set_then_default_is_used():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int, default=None),
            schema.input_field("field1", type=schema.Int, default=42),
        ),
    )

    input_value = Input()
    assert_that(input_value, has_attrs(
        field0=None,
        field1=42,
    ))


def test_given_input_field_has_no_default_when_input_field_is_not_set_then_error_is_raised():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int),
        ),
    )

    error = pytest.raises(GraphError, lambda: Input())
    assert_that(str(error.value), equal_to("Input is missing required field field0"))


def test_when_passing_unknown_field_values_into_input_object_then_error_is_raised():
    Input = schema.InputObjectType(
        "Input",
        fields=(
            schema.input_field("field0", type=schema.Int),
        ),
    )

    error = pytest.raises(GraphError, lambda: Input(field0=0, field1=1))
    assert_that(str(error.value), equal_to("Input has no field field1"))


def test_given_field_arg_has_default_when_field_arg_is_not_set_then_default_is_used():
    Root = schema.ObjectType(
        "Root",
        fields=(
            schema.field("one", type=schema.Int, params=[
                schema.param("arg0", type=schema.Int, default=None),
                schema.param("arg1", type=schema.Int, default=42),
            ]),
        ),
    )

    field_query = Root.fields.one()
    assert_that(field_query.args, has_attrs(
        arg0=None,
        arg1=42,
    ))


def test_given_field_arg_has_no_default_when_field_arg_is_not_set_then_error_is_raised():
    Root = schema.ObjectType(
        "Root",
        fields=(
            schema.field("one", type=schema.Int, params=[
                schema.param("arg0", type=schema.Int),
            ]),
        ),
    )

    error = pytest.raises(GraphError, lambda: Root.fields.one())
    assert_that(str(error.value), equal_to("field one is missing required argument arg0"))


def test_arguments_are_coerced():
    Root = schema.ObjectType(
        "Root",
        fields=(
            schema.field("one", type=schema.Int, params=[
                schema.param("arg", type=schema.Int),
            ]),
        ),
    )

    error = pytest.raises(GraphError, lambda: Root.fields.one(Root.fields.one.params.arg(None)))
    assert_that(str(error.value), equal_to("cannot coerce None to Int"))


class TestCoerce(object):
    def test_boolean_type_coerces_bools_to_bools(self):
        self._assert_coercion(schema.Boolean, True, True)
        self._assert_coercion(schema.Boolean, False, False)

    def test_cannot_coerce_none_to_boolean(self):
        self._assert_coercion_failure(schema.Boolean, None, "cannot coerce None to Boolean")

    def test_cannot_coerce_true_string_to_boolean(self):
        self._assert_coercion_failure(schema.Boolean, "True", "cannot coerce 'True' to Boolean")
        self._assert_coercion_failure(schema.Boolean, "true", "cannot coerce 'true' to Boolean")

    def test_float_type_coerces_floats_to_floats(self):
        self._assert_coercion(schema.Float, 1.0, 1.0)
        self._assert_coercion(schema.Float, 1.1, 1.1)

    def test_float_type_coerces_ints_to_floats(self):
        self._assert_coercion(schema.Float, 1, 1.0)

    def test_cannot_coerce_large_int_to_float(self):
        self._assert_coercion_failure(schema.Float, 11111111111111111111111111111111111, "cannot coerce 11111111111111111111111111111111111 to Float")

    def test_cannot_coerce_none_to_float(self):
        self._assert_coercion_failure(schema.Float, None, "cannot coerce None to Float")

    def test_cannot_coerce_numeric_string_to_float(self):
        self._assert_coercion_failure(schema.Float, "1.0", "cannot coerce '1.0' to Float")

    def test_float_type_coerces_ints_to_ints(self):
        self._assert_coercion(schema.Int, 1, 1)
        self._assert_coercion(schema.Int, -42, -42)

    def test_cannot_coerce_none_to_int(self):
        self._assert_coercion_failure(schema.Int, None, "cannot coerce None to Int")

    def test_cannot_coerce_numeric_string_to_int(self):
        self._assert_coercion_failure(schema.Float, "1", "cannot coerce '1' to Float")

    def test_string_type_coerces_strings_to_strings(self):
        self._assert_coercion(schema.String, "1", "1")
        self._assert_coercion(schema.String, "", "")
        self._assert_coercion(schema.String, "The Ballad of Mr Steak", "The Ballad of Mr Steak")

    def test_cannot_coerce_none_to_string(self):
        self._assert_coercion_failure(schema.String, None, "cannot coerce None to String")

    def test_cannot_coerce_int_to_string(self):
        self._assert_coercion_failure(schema.String, 1, "cannot coerce 1 to String")

    def test_enum_type_coerces_enum_values_to_enum_values(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        self._assert_coercion(DirectionGraphType, Direction.up, Direction.up)
        self._assert_coercion(DirectionGraphType, Direction.down, Direction.down)

    def test_cannot_coerce_none_to_enum(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        self._assert_coercion_failure(DirectionGraphType, None, "cannot coerce None to Direction")

    def test_cannot_coerce_string_to_enum(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        self._assert_coercion_failure(DirectionGraphType, "up", "cannot coerce 'up' to Direction")

    def test_lists_type_coerces_elements_to_element_type(self):
        self._assert_coercion(schema.ListType(schema.Float), [1, 2], [1.0, 2.0])
        assert_that(type(schema.ListType(schema.Float).coerce([1])[0]), equal_to(float))

    def test_nullable_type_coerces_non_null_value_to_element_type(self):
        self._assert_coercion(schema.NullableType(schema.Float), 1, 1.0)

    def test_nullable_type_coerces_null_to_null(self):
        self._assert_coercion(schema.NullableType(schema.Float), None, None)

    def test_input_object_type_coerces_instances_to_same_value(self):
        UserInput = schema.InputObjectType("UserInput", fields=lambda: (
            schema.input_field("name", type=schema.String),
        ))

        self._assert_coercion(UserInput, UserInput(name="Bob"), UserInput(name="Bob"))

    def test_cannot_coerce_instances_of_input_object_type_to_other_input_object_type(self):
        PersonInput = schema.InputObjectType("PersonInput", fields=lambda: (
            schema.input_field("name", type=schema.String),
        ))

        UserInput = schema.InputObjectType("UserInput", fields=lambda: (
            schema.input_field("name", type=schema.String),
        ))

        self._assert_coercion_failure(UserInput, PersonInput(name="Bob"), "cannot coerce PersonInput(name='Bob') to UserInput")

    def test_cannot_coerce_none_to_input_object_type(self):
        UserInput = schema.InputObjectType("UserInput", fields=lambda: (
            schema.input_field("name", type=schema.String),
        ))

        self._assert_coercion_failure(UserInput, None, "cannot coerce None to UserInput")

    def _assert_coercion(self, graph_type, value, expected):
        coerced = graph_type.coerce(value)
        assert_that(coerced, equal_to(expected))
        assert_that(type(coerced), equal_to(type(expected)))

    def _assert_coercion_failure(self, graph_type, value, expected_error):
        error = pytest.raises(GraphError, lambda: graph_type.coerce(value))
        assert_that(str(error.value), equal_to(expected_error))


class TestAdd(object):
    def test_scalar_queries_merge_into_scalar_query(self):
        query = schema.Boolean() + schema.Boolean()
        assert_that(query, is_query(schema.Boolean()))

    def test_adding_scalar_query_to_other_query_raises_type_error(self):
        pytest.raises(TypeError, lambda: schema.Boolean() + schema.ObjectType("Obj", fields=()))

    def test_adding_scalar_queries_of_different_type_raises_type_error(self):
        error = pytest.raises(TypeError, lambda: schema.Boolean() + schema.Int())
        assert_that(str(error.value), equal_to("cannot add queries for different scalar types: Boolean and Int"))

    def test_enum_queries_merge_into_enum_query(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        query = DirectionGraphType() + DirectionGraphType()
        assert_that(query, is_query(DirectionGraphType()))

    def test_adding_enum_query_to_other_query_raises_type_error(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        pytest.raises(TypeError, lambda: DirectionGraphType() + schema.ObjectType("Obj", fields=()))

    def test_adding_enum_queries_of_different_type_raises_type_error(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        class Size(enum.Enum):
            big = "big"
            small = "small"

        SizeGraphType = schema.EnumType(Size)

        error = pytest.raises(TypeError, lambda: DirectionGraphType() + SizeGraphType())
        assert_that(str(error.value), equal_to("cannot add queries for different enum types: Direction and Size"))

    def test_merged_object_query_has_fields_from_operand_queries(self):
        Song = schema.ObjectType("Song", fields=(
            schema.field("title", type=schema.String),
            schema.field("length", type=schema.Int),
        ))
        query = Song(schema.key("title", Song.fields.title())) + Song(schema.key("length", Song.fields.length()))
        assert_that(query, is_query(Song(
            schema.key("title", Song.fields.title()),
            schema.key("length", Song.fields.length()),
        )))

    def test_fields_are_recursively_merged(self):
        User = schema.ObjectType(
            "User",
            fields=lambda: (
                schema.field("address", type=Address),
            ),
        )

        Address = schema.ObjectType(
            "Address",
            fields=lambda: (
                schema.field("first_line", type=schema.String),
                schema.field("city", type=schema.String),
                schema.field("postcode", type=schema.String),
            ),
        )

        left_query = User(
            schema.key("address", User.fields.address(
                schema.key("first_line", Address.fields.first_line()),
                schema.key("city", Address.fields.city()),
            )),
        )
        right_query = User(
            schema.key("address", User.fields.address(
                schema.key("city", Address.fields.city()),
                schema.key("postcode", Address.fields.postcode()),
            )),
        )

        assert_that(left_query + right_query, is_query(
            User(
                schema.key("address", User.fields.address(
                    schema.key("first_line", Address.fields.first_line()),
                    schema.key("city", Address.fields.city()),
                    schema.key("postcode", Address.fields.postcode()),
                )),
            ),
        ))

    def test_fields_with_same_key_for_different_types_are_kept_separate(self):
        Item = schema.InterfaceType("Item", fields=())
        Song = schema.ObjectType("Song", interfaces=(Item, ), fields=(
            schema.field("title", type=schema.String),
        ))
        Book = schema.ObjectType("Book", interfaces=(Item, ), fields=(
            schema.field("title", type=schema.String),
        ))
        query = (
            Item(schema.key("title", Song.fields.title())) +
            Item(schema.key("title", Book.fields.title()))
        )
        assert_that(query, is_query(Item(
            schema.key("title", Song.fields.title()),
            schema.key("title", Book.fields.title()),
        )))

    def test_adding_object_query_to_other_query_raises_type_error(self):
        pytest.raises(TypeError, lambda: schema.ObjectType("Obj", fields=()) + schema.Boolean())

    def test_list_query_merges_element_queries(self):
        Song = schema.ObjectType("Song", fields=(
            schema.field("title", type=schema.String),
            schema.field("length", type=schema.Int),
        ))
        query = (
            schema.ListType(Song)(schema.key("title", Song.fields.title())) +
            schema.ListType(Song)(schema.key("length", Song.fields.length()))
        )
        assert_that(query, is_query(schema.ListType(Song)(
            schema.key("title", Song.fields.title()),
            schema.key("length", Song.fields.length()),
        )))

    def test_adding__query_to_non_list_query_raises_type_error(self):
        pytest.raises(TypeError, lambda: schema.ListType(schema.Boolean)() + schema.Boolean())

    def test_adding_list_query_to_list_query_of_different_element_type_raises_type_error(self):
        error = pytest.raises(TypeError, lambda: schema.ListType(schema.Boolean)() + schema.ListType(schema.Int)())
        assert_that(str(error.value), equal_to("cannot add queries for lists with different element types: Boolean and Int"))

    def test_nullable_query_merges_element_queries(self):
        Song = schema.ObjectType("Song", fields=(
            schema.field("title", type=schema.String),
            schema.field("length", type=schema.Int),
        ))
        query = (
            schema.NullableType(Song)(schema.key("title", Song.fields.title())) +
            schema.NullableType(Song)(schema.key("length", Song.fields.length()))
        )
        assert_that(query, is_query(schema.NullableType(Song)(
            schema.key("title", Song.fields.title()),
            schema.key("length", Song.fields.length()),
        )))

    def test_adding_nullable_query_to_non_null_query_raises_type_error(self):
        pytest.raises(TypeError, lambda: schema.NullableType(schema.Boolean)() + schema.Boolean())

    def test_adding_nullable_query_to_nullable_query_of_different_element_type_raises_type_error(self):
        error = pytest.raises(TypeError, lambda: schema.NullableType(schema.Boolean)() + schema.NullableType(schema.Int)())
        assert_that(str(error.value), equal_to("cannot add queries for nullables with different element types: Boolean and Int"))

class TestForType(object):
    def test_scalar_query_for_type_is_scalar_query(self):
        query = schema.Boolean().for_type(schema.Boolean)
        assert_that(query, is_query(schema.Boolean()))

    def test_cannot_change_type_of_scalar_query(self):
        error = pytest.raises(TypeError, lambda: schema.Boolean().for_type(schema.String))
        assert_that(str(error.value), equal_to("cannot coerce query for Boolean to query for String"))

    def test_enum_query_for_type_is_enum_query(self):
        class Season(enum.Enum):
            winter = "WINTER"
            spring = "SPRING"
            summer = "SUMMER"
            autumn = "AUTUMN"

        SeasonGraphType = schema.EnumType(Season)
        query = SeasonGraphType().for_type(SeasonGraphType)
        assert_that(query, is_query(SeasonGraphType()))

    def test_cannot_change_type_of_enum_query(self):
        class Season(enum.Enum):
            winter = "WINTER"

        class Quarter(enum.Enum):
            q1 = "Q1"

        SeasonGraphType = schema.EnumType(Season)
        QuarterGraphType = schema.EnumType(Quarter)

        error = pytest.raises(TypeError, lambda: SeasonGraphType().for_type(QuarterGraphType))
        assert_that(str(error.value), equal_to("cannot coerce query for Season to query for Quarter"))

    def test_converting_query_for_interface_to_object_filters_fields_to_those_for_object(self):
        Item = schema.InterfaceType("Item", fields=(
            schema.field("title", type=schema.String),
        ))
        Song = schema.ObjectType("Song", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
            schema.field("title", type=schema.String),
        ))
        Book = schema.ObjectType("Book", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
            schema.field("title", type=schema.String),
        ))
        query = Item(
            schema.key("title", Item.fields.title()),
            schema.key("length", Song.fields.length()),
            schema.key("length", Book.fields.length()),
        )

        assert_that(query.for_type(Song), is_query(Song(
            schema.key("title", Song.fields.title()),
            schema.key("length", Song.fields.length()),
        )))

    def test_cannot_convert_query_for_interface_to_unrelated_object(self):
        Item = schema.InterfaceType("Item", fields=(
            schema.field("title", type=schema.String),
        ))
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", type=schema.String),
        ))
        query = Item(
            schema.key("title", Item.fields.title()),
        )

        error = pytest.raises(TypeError, lambda: query.for_type(Book))
        assert_that(str(error.value), equal_to("cannot coerce query for Item to query for Book"))

    def test_object_type_for_type_retains_fields_for_subtypes(self):
        Item = schema.InterfaceType("Item", fields=(
            schema.field("title", type=schema.String),
        ))
        Song = schema.ObjectType("Song", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
            schema.field("title", type=schema.String),
        ))
        Book = schema.ObjectType("Book", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
            schema.field("title", type=schema.String),
        ))
        query = Item(
            schema.key("title", Item.fields.title()),
            schema.key("length", Song.fields.length()),
            schema.key("length", Book.fields.length()),
        )

        assert_that(query.for_type(Item), is_query(Item(
            schema.key("title", Item.fields.title()),
            schema.key("length", Song.fields.length()),
            schema.key("length", Book.fields.length()),
        )))

    def test_list_type_for_type_calls_for_type_on_element_query(self):
        Item = schema.InterfaceType("Item", fields=(
        ))
        Song = schema.ObjectType("Song", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
        ))
        Book = schema.ObjectType("Book", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
        ))
        query = schema.ListType(Item)(
            schema.key("length", Song.fields.length()),
            schema.key("length", Book.fields.length()),
        ).for_type(schema.ListType(Song))

        assert_that(query, is_query(schema.ListType(Song)(
            schema.key("length", Song.fields.length()),
        )))

    def test_cannot_change_type_of_list_query_to_non_list_query(self):
        query = schema.ListType(schema.Boolean)()

        error = pytest.raises(TypeError, lambda: query.for_type(schema.NullableType(schema.Boolean)))
        assert_that(str(error.value), equal_to("cannot coerce query for List(Boolean) to query for Nullable(Boolean)"))

    def test_nullable_type_for_type_calls_for_type_on_element_query(self):
        Item = schema.InterfaceType("Item", fields=(
        ))
        Song = schema.ObjectType("Song", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
        ))
        Book = schema.ObjectType("Book", interfaces=(Item, ), fields=(
            schema.field("length", type=schema.Int),
        ))
        query = schema.NullableType(Item)(
            schema.key("length", Song.fields.length()),
            schema.key("length", Book.fields.length()),
        ).for_type(schema.NullableType(Song))

        assert_that(query, is_query(schema.NullableType(Song)(
            schema.key("length", Song.fields.length()),
        )))

    def test_cannot_change_type_of_nullable_query_to_non_nullable_query(self):
        query = schema.NullableType(schema.Boolean)()

        error = pytest.raises(TypeError, lambda: query.for_type(schema.Boolean))
        assert_that(str(error.value), equal_to("cannot coerce query for Nullable(Boolean) to query for Boolean"))


class TestFieldQuery(object):
    def test_creating_field_query_specialises_type_of_type_query(self):
        Root = schema.ObjectType("Root", fields=lambda: (
            schema.field("song", type=Song),
        ))
        Item = schema.InterfaceType("Item", fields=(
            schema.field("title", type=schema.String),
        ))
        Song = schema.ObjectType("Song", interfaces=(Item, ), fields=(
            schema.field("title", type=schema.String),
        ))
        field_query = Root.fields.song.query(key="song", args=(), type_query=Item(
            schema.key("title", Item.fields.title()),
        ))

        assert_that(field_query, is_query(
            Root.fields.song.query(key="song", args=(), type_query=Song(
                schema.key("title", Song.fields.title()),
            )),
        ))


class TestQueryString(object):
    def test_scalar_query_string_includes_type(self):
        query = schema.Int()
        assert_that(str(query), equal_to(dedent("""
            ScalarQuery(type=Int)
        """)))

    def test_enum_query_string_includes_type(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        query = DirectionGraphType()

        assert_that(str(query), equal_to(dedent("""
            EnumQuery(type=Direction)
        """)))

    def test_list_query_string_includes_element_query(self):
        query = schema.ListType(schema.Int)()
        assert_that(str(query), equal_to(dedent("""
            ListQuery(
                type=List(Int),
                element_query=ScalarQuery(type=Int),
            )
        """)))

    def test_nullable_query_string_includes_element_query(self):
        query = schema.NullableType(schema.Int)()
        assert_that(str(query), equal_to(dedent("""
            NullableQuery(
                type=Nullable(Int),
                element_query=ScalarQuery(type=Int),
            )
        """)))

    def test_object_query_string_includes_type_and_field_queries(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
            schema.field("publication_year", schema.Int),
        ))

        query = Book(
            schema.key("title", Book.fields.title()),
            schema.key("year", Book.fields.publication_year()),
        )

        assert_that(str(query), equal_to(dedent("""
            ObjectQuery(
                type=Book,
                field_queries=(
                    FieldQuery(
                        key="title",
                        field=Book.fields.title,
                        type_query=ScalarQuery(type=String),
                        args=(),
                    ),
                    FieldQuery(
                        key="year",
                        field=Book.fields.publication_year,
                        type_query=ScalarQuery(type=Int),
                        args=(),
                    ),
                ),
            )
        """)))

    def test_field_query_string_includes_key_and_field_and_type_query(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))

        query = schema.key("title", Book.fields.title())

        assert_that(str(query), equal_to(dedent("""
            FieldQuery(
                key="title",
                field=Book.fields.title,
                type_query=ScalarQuery(type=String),
                args=(),
            )
        """)))

    def test_field_can_be_from_subtype(self):
        Item = schema.InterfaceType("Item", fields=())

        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ), interfaces=(Item, ))

        query = schema.key("title", Book.fields.title())

        assert_that(str(query), equal_to(dedent("""
            FieldQuery(
                key="title",
                field=Book.fields.title,
                type_query=ScalarQuery(type=String),
                args=(),
            )
        """)))

    def test_field_query_string_includes_args(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String, params=(
                schema.param("truncate", schema.Int),
            )),
        ))

        query = schema.key("title", Book.fields.title(Book.fields.title.params.truncate(42)))

        assert_that(str(query), equal_to(dedent("""
            FieldQuery(
                key="title",
                field=Book.fields.title,
                type_query=ScalarQuery(type=String),
                args=(
                    Book.fields.title.params.truncate(42),
                ),
            )
        """)))


class TestField(object):
    def test_calling_field_with_unknown_types_raises_error(self):
        field = schema.field("x", type=schema.Int)
        error = pytest.raises(GraphError, lambda: field(42))
        assert_that(str(error.value), equal_to("unexpected argument: 42\nExpected arguments of type Argument or FieldQuery but had type int"))


class TestObjectType(object):
    def test_interface_can_be_set_as_iterable(self):
        Interface = schema.InterfaceType("Interface", fields=())
        Obj = schema.ObjectType("Obj", fields=(), interfaces=(Interface, ))
        assert_that(Obj.interfaces, contains_exactly(Interface))

    def test_interface_can_be_set_as_function_returning_iterable(self):
        Interface = schema.InterfaceType("Interface", fields=())
        Obj = schema.ObjectType("Obj", fields=(), interfaces=lambda: (Interface, ))
        assert_that(Obj.interfaces, contains_exactly(Interface))


class TestCollectTypes(object):
    def test_boolean_has_no_child_types(self):
        assert_that(schema.collect_types((schema.Boolean, )), contains_exactly(schema.Boolean))

    def test_float_has_no_child_types(self):
        assert_that(schema.collect_types((schema.Float, )), contains_exactly(schema.Float))

    def test_int_has_no_child_types(self):
        assert_that(schema.collect_types((schema.Int, )), contains_exactly(schema.Int))

    def test_string_has_no_child_types(self):
        assert_that(schema.collect_types((schema.String, )), contains_exactly(schema.String))

    def test_enum_has_no_child_types(self):
        class Direction(enum.Enum):
            up = "up"
            down = "down"

        DirectionGraphType = schema.EnumType(Direction)

        assert_that(schema.collect_types((DirectionGraphType, )), contains_exactly(DirectionGraphType))

    def test_interface_type_has_field_types_in_child_types(self):
        User = schema.InterfaceType("User", fields=lambda: (
            schema.field("name", type=schema.String),
        ))
        collected_types = schema.collect_types((User, ))
        assert_that(collected_types, includes(schema.String))

    def test_input_object_type_has_field_types_in_child_types(self):
        UserInput = schema.InputObjectType("UserInput", fields=lambda: (
            schema.field("name", type=schema.String),
        ))
        collected_types = schema.collect_types((UserInput, ))
        assert_that(collected_types, includes(schema.String))

    def test_interface_type_has_field_param_types_in_child_types(self):
        User = schema.InterfaceType("User", fields=lambda: (
            schema.field("name", type=schema.String, params=(
                schema.param("long", type=schema.Boolean),
            )),
        ))
        collected_types = schema.collect_types((User, ))
        assert_that(collected_types, includes(schema.Boolean))

    def test_list_type_has_element_type_as_child_type(self):
        collected_types = schema.collect_types((schema.ListType(schema.String), ))
        assert_that(collected_types, contains_exactly(schema.ListType(schema.String), schema.String))

    def test_nullable_type_has_element_type_as_child_type(self):
        collected_types = schema.collect_types((schema.NullableType(schema.String), ))
        assert_that(collected_types, contains_exactly(schema.NullableType(schema.String), schema.String))

    def test_object_type_has_field_types_in_child_types(self):
        User = schema.ObjectType("User", fields=lambda: (
            schema.field("name", type=schema.String),
        ))
        collected_types = schema.collect_types((User, ))
        assert_that(collected_types, includes(schema.String))

    def test_object_type_has_field_param_types_in_child_types(self):
        User = schema.ObjectType("User", fields=lambda: (
            schema.field("name", type=schema.String, params=(
                schema.param("long", type=schema.Boolean),
            )),
        ))
        collected_types = schema.collect_types((User, ))
        assert_that(collected_types, includes(schema.Boolean))

    def test_object_type_has_interface_types_in_child_types(self):
        Person = schema.InterfaceType("Person", fields=lambda: (
            schema.field("name", type=schema.String),
        ))
        User = schema.ObjectType("User", fields=lambda: (
            schema.field("name", type=schema.String),
        ), interfaces=(Person, ))
        collected_types = schema.collect_types((User, ))
        assert_that(collected_types, includes(Person))


@pytest.mark.parametrize("graph_type, element_type", (
    (schema.ListType(schema.Boolean), schema.Boolean),
    (schema.NullableType(schema.Boolean), schema.Boolean),
    (schema.Boolean, schema.Boolean),
    (schema.ListType(schema.ListType(schema.Boolean)), schema.Boolean),
    (schema.NullableType(schema.NullableType(schema.Boolean)), schema.Boolean),
    (schema.ListType(schema.NullableType(schema.Boolean)), schema.Boolean),
))
def test_to_element_type(graph_type, element_type):
    assert_that(schema.to_element_type(graph_type), equal_to(element_type))


def dedent(value):
    return textwrap.dedent(value).strip()
