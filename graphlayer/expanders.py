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
    field_arg_handlers = {}
    
    @expander(type)
    def expand_root(graph, query):
        def handle_args(field_query):
            arg_handler = field_arg_handlers.get(field_query.field)
            # TODO: handle unhandled args
            # TODO: argument handling in non-root types
            if arg_handler is None:
                return field_query.type_query
            else:
                args = ObjectResult(iterables.to_dict(
                    (arg.parameter.name, arg.value)
                    for arg in field_query.args
                ))
                return arg_handler(graph, field_query.type_query, args)
        
        return ObjectResult(iterables.to_dict(
            (key, graph.expand(handle_args(field_query)))
            for key, field_query in query.fields.items()
        ))
    
    def arg_handler(field):
        def add_handler(handler):
            field_arg_handlers[field] = handler
        
        return add_handler
    
    expand_root.arg_handler = arg_handler
    
    return expand_root
