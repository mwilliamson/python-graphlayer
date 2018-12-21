from precisely import assert_that, equal_to
import pytest

from graphlayer import schema
from graphlayer.representations import ObjectResult


def test_when_field_does_not_exist_on_object_type_then_error_is_raised():
    book = schema.ObjectType("Book", fields=(
        schema.field("title", schema.String),
    ))
    
    error = pytest.raises(ValueError, lambda: book.fields.author)
    
    assert_that(str(error.value), equal_to("Book has no field author"))


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

    def test_objects_are_converted_to_dicts(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        query = Book(book_title=Book.fields.title())
        value = ObjectResult(dict(book_title="Orbiting the Giant Hairball"))
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
        query = Book(author=Book.fields.author(name=Author.fields.name()))
        value = ObjectResult(dict(
            author=ObjectResult(dict(
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
        query = NullableBook(book_title=Book.fields.title())
        assert_that(query.to_json_value(None), equal_to(None))

    def test_when_value_is_not_none_then_nullable_value_is_converted_using_element_query(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        NullableBook = schema.NullableType(Book)
        query = NullableBook(book_title=Book.fields.title())
        value = ObjectResult(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value(value), equal_to({
            "book_title": "Orbiting the Giant Hairball",
        }))

    def test_lists_convert_elements_to_json_values(self):
        Book = schema.ObjectType("Book", fields=(
            schema.field("title", schema.String),
        ))
        BookList = schema.ListType(Book)
        query = BookList(book_title=Book.fields.title())
        value = ObjectResult(dict(book_title="Orbiting the Giant Hairball"))
        assert_that(query.to_json_value([value]), equal_to([
            {
                "book_title": "Orbiting the Giant Hairball",
            },
        ]))
