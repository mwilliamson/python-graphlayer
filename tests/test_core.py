from precisely import assert_that, equal_to
import pytest

import graphlayer.core as g


def test_given_expander_has_no_dependencies_when_expand_is_called_with_empty_context_then_expander_is_directly_called():
    @g.expander("root", "integer_representation")
    def expand_root(graph):
        return 42
    
    expanders = [expand_root]
    
    result = g.create_graph(expanders).expand("root", "integer_representation")
    
    assert_that(result, equal_to(42))


def test_given_expander_has_no_dependencies_when_expand_is_called_with_non_empty_context_then_context_is_ignored():
    @g.expander("root", "integer_representation")
    def expand_root(graph):
        return 42
    
    expanders = [expand_root]
    
    result = g.create_graph(expanders).expand("root", "integer_representation", context={"a": 1})
    
    assert_that(result, equal_to(42))


def test_when_expand_is_called_then_expander_is_passed_the_graph():
    @g.expander("root", "integer_representation")
    def expand_root(graph):
        return graph.expand("leaf", "integer_representation")
    
    @g.expander("leaf", "integer_representation")
    def expand_leaf(graph):
        return 42
    
    expanders = [expand_root, expand_leaf]
    
    result = g.create_graph(expanders).expand("root", "integer_representation")
    
    assert_that(result, equal_to(42))


def test_given_expander_has_dependencies_when_expand_is_called_with_context_then_dependencies_are_passed_to_expander():
    @g.expander("root", "integer_representation", dependencies={"result": "answer"})
    def expand_root(graph, result):
        return result
    
    expanders = [expand_root]
    
    result = g.create_graph(expanders).expand(
        "root",
        "integer_representation",
        context=dict(answer=42),
    )
    
    assert_that(result, equal_to(42))


def test_given_expander_has_dependencies_when_expand_is_called_without_dependencies_then_error_is_raised():
    @g.expander("root", "integer_representation", dependencies={"result": "answer"})
    def expand_root(graph, result):
        return result
    
    expanders = [expand_root]
    
    error = pytest.raises(g.NoRouteError, lambda: g.create_graph(expanders).expand(
        "root",
        "integer_representation",
        context={"a": 1},
    ))
    
    assert_that(str(error.value), equal_to(
        "Could not find route to {root!r} with context {context!r}".format(root="root", context={"a": 1}),
    ))
