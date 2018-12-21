from precisely import assert_that, equal_to
import pytest

from graphlayer import schema


def test_when_field_does_not_exist_on_object_type_then_error_is_raised():
    book = schema.ObjectType("Book", fields=(
        schema.field("title", schema.String),
    ))
    
    error = pytest.raises(ValueError, lambda: book.author)
    
    assert_that(str(error.value), equal_to("Book has no field author"))
