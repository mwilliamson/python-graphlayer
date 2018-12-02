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


def root_object_expander(type):
    field_handlers = {}

    @expander(type)
    def expand_root(graph, query):
        def expand_field(field_query):
            # TODO: handle unhandled args
            # TODO: argument handling in non-root types
            if field_query.args:
                return field_handlers[field_query.field](graph, field_query.type_query, field_query.args)
            else:
                return graph.expand(field_query.type_query)
        
        return ObjectResult(iterables.to_dict(
            (key, expand_field(field_query))
            for key, field_query in query.fields.items()
        ))
    
    def field(field):
        def add_handler(handle):
            field_handlers[field] = handle
            return handle
        
        return add_handler
    
    expand_root.field = field
    
    return expand_root
