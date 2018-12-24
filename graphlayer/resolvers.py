from . import iterables
from .core import resolver


def constant_object_resolver(type, values):
    @resolver(type)
    def resolve(graph, query):
        return query.create_object(iterables.to_dict(
            (key, values[field_query.field.name])
            for key, field_query in query.fields.items()
        ))
    
    return resolve


def root_object_resolver(type):
    field_handlers = {}

    @resolver(type)
    def resolve_root(graph, query):
        def resolve_field(field_query):
            # TODO: handle unhandled args
            # TODO: argument handling in non-root types
            return field_handlers[field_query.field](graph, field_query.type_query, field_query.args)
        
        return query.create_object(iterables.to_dict(
            (key, resolve_field(field_query))
            for key, field_query in query.fields.items()
        ))
    
    def field(field):
        def add_handler(handle):
            field_handlers[field] = handle
            return handle
        
        return add_handler
    
    resolve_root.field = field
    
    return resolve_root
