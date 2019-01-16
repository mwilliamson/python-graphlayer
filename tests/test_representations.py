from graphlayer.representations import Object
from precisely import assert_that, equal_to


def test_empty_object_has_repr_with_values():
    obj = Object({"a": 1})
    assert_that(repr(obj), equal_to("Object({'a': 1})"))
