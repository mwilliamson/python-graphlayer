from . import iterables
from .core import expander
from .representations import object_representation, ObjectResult
from .schema import object_query


def constant_object_expander(type, values):
    @expander(type, object_representation, dependencies=dict(query=object_query))
    def expand(graph, query):
        return ObjectResult(iterables.to_dict(
            (key, values[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    return expand


def root_object_expander(type, field_contexts):
    @expander(type, object_representation, dict(query=object_query))
    def expand_root(graph, query):
        def resolve_field(field_query):
            context = field_contexts[field_query.field].copy()
            context[object_query] = field_query.type_query
            return graph.expand(
                field_query.field.type,
                object_representation,
                context=context,
            )
        
        return ObjectResult(iterables.to_dict(
            (key, resolve_field(field_query))
            for key, field_query in query.fields.items()
        ))
    
    return expand_root
