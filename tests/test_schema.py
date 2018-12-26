import enum

from precisely import assert_that, equal_to, has_attrs
import pytest

from graphlayer import schema
from graphlayer.representations import Object
from .matchers import is_query


def test_when_param_does_not_exist_on_params_then_error_is_raised():
    params = schema.Params("book", {})
    
    error = pytest.raises(ValueError, lambda: params.author)
    
    assert_that(str(error.value), equal_to("book has no param author"))


def test_when_field_does_not_exist_on_object_type_then_error_is_raised():
    book = schema.ObjectType("Book", fields=(
        schema.field("title", schema.String),
    ))
    
    error = pytest.raises(ValueError, lambda: book.fields.author)
    
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
    
    error = pytest.raises(ValueError, lambda: Input())
    assert_that(str(error.value), equal_to("missing value for field0"))


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
    
    error = pytest.raises(ValueError, lambda: Root.fields.one())
    assert_that(str(error.value), equal_to("missing value for arg0"))


class TestAdd(object):
    def test_scalar_queries_merge_into_scalar_query(self):
        query = schema.Boolean() + schema.Boolean()
        assert_that(query, is_query(schema.Boolean()))

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


class TestForType(object):
    def test_scalar_query_for_type_is_scalar_query(self):
        query = schema.Boolean().for_type(schema.Boolean())
        assert_that(query, is_query(schema.Boolean()))
    
    def test_object_type_for_type_filters_fields_to_those_for_type(self):
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


class TestToJsonValue(object):
    def test_bool_is_unchanged(self):
        query = schema.Boolean()
        assert_that(query.to_json_value(True), equal_to(True))

    def test_float_is_unchanged(self):
        query = schema.Float()
        assert_that(query.to_json_value(4.2), equal_to(4.2))

    def test_int_is_unchanged(self):
        query = schema.Int()
        assert_that(query.to_json_value(42), equal_to(42))

    def test_string_is_unchanged(self):
        query = schema.String()
        assert_that(query.to_json_value("42"), equal_to("42"))

    def test_enums_are_converted_to_strings(self):
        class Season(enum.Enum):
            winter = "WINTER"
            spring = "SPRING"
            summer = "SUMMER"
            autumn = "AUTUMN"

        SeasonGraphType = schema.EnumType(Season)
        query = SeasonGraphType()
        assert_that(query.to_json_value(Season.winter), equal_to("WINTER"))

    def test_objects_are_converted_to_dicts(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        query = Book(schema.key("book_title", Book.fields.title()))
        value = Object(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value(value), equal_to({
            "book_title": "Orbiting the Giant Hairball",
        }))

    def test_objects_convert_fields_to_json_values(self):
        Author = schema.ObjectType("Author", fields=(
            schema.field("name", schema.String),
        ))
        Book = schema.ObjectType("Book", fields=(
            schema.field("author", Author),
        ))
        query = Book(
            schema.key("author", Book.fields.author(
                schema.key("name", Author.fields.name()),
            )),
        )
        value = Object(dict(
            author=Object(dict(
                name="Gordon A. Mackenzie",
            )),
        ))
        assert_that(query.to_json_value(value), equal_to({
            "author": {
                "name": "Gordon A. Mackenzie",
            },
        }))

    def test_when_value_is_none_then_nullable_value_is_converted_to_none(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        NullableBook = schema.NullableType(Book)
        query = NullableBook(schema.key("book_title", Book.fields.title()))
        assert_that(query.to_json_value(None), equal_to(None))

    def test_when_value_is_not_none_then_nullable_value_is_converted_using_element_query(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        NullableBook = schema.NullableType(Book)
        query = NullableBook(schema.key("book_title", Book.fields.title()))
        value = Object(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value(value), equal_to({
            "book_title": "Orbiting the Giant Hairball",
        }))

    def test_lists_convert_elements_to_json_values(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        BookList = schema.ListType(Book)
        query = BookList(schema.key("book_title", Book.fields.title()))
        value = Object(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value([value]), equal_to([
            {
                "book_title": "Orbiting the Giant Hairball",
            },
        ]))
