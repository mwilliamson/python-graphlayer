from . import iterables
from .core import expander
from .representations import ObjectResult


def constant_object_expander(type, values):
    @expander(type)
    def expand(graph, query):
        return ObjectResult(iterables.to_dict(
            (key, values[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    return expand


def root_object_expander(type, field_contexts):
    @expander(type)
    def expand_root(graph, query):
        return ObjectResult(iterables.to_dict(
            (key, graph.expand(field_query.type_query))
            for key, field_query in query.fields.items()
        ))
    
    return expand_root
