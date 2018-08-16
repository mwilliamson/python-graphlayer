from . import iterables
from .core import expander
from .representations import object_query, object_representation, ObjectResult


def constant_object_expander(type, values):
    @expander(type, object_representation, dependencies=dict(query=object_query))
    def expand(graph, query):
        return ObjectResult(iterables.to_dict(
            (key, values[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    return expand
