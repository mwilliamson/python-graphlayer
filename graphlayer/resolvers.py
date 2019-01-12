from . import core, iterables


def constant_object_resolver(type, values):
    @core.resolver(type)
    def resolve(graph, query):
        return query.create_object(iterables.to_dict(
            (field_query.key, values[field_query.field.name])
            for field_query in query.field_queries
        ))

    return resolve


def root_object_resolver(type):
    field_handlers = {}

    @core.resolver(type)
    @core.dependencies(injector=core.Injector)
    def resolve_root(graph, query, *, injector):
        def resolve_field(field_query):
            # TODO: handle unhandled args
            field_resolver = field_handlers[field_query.field]
            return injector.call_with_dependencies(field_resolver, graph, field_query.type_query, field_query.args)

        return query.create_object(iterables.to_dict(
            (field_query.key, resolve_field(field_query))
            for field_query in query.field_queries
        ))

    def field(field):
        def add_handler(handle):
            field_handlers[field] = handle
            return handle

        return add_handler

    resolve_root.field = field

    return resolve_root
