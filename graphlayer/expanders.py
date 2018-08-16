from . import iterables
from .core import expander
from .representations import ObjectResult


def constant_object_expander(type, values):
    @expander(type, ObjectResult)
    def expand(graph, query):
        return ObjectResult(iterables.to_dict(
            (key, values[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    return expand
