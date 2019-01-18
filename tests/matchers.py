from precisely import has_attrs, is_instance, is_mapping, is_sequence

from graphlayer import schema


def is_query(query):
    if isinstance(query, schema.ScalarQuery):
        return is_instance(schema.ScalarQuery)

    elif isinstance(query, schema.EnumQuery):
        return is_instance(schema.EnumQuery)

    elif isinstance(query, schema.FieldQuery):
        return has_attrs(
            key=query.key,
            field=query.field,
            type_query=is_query(query.type_query),
            args=has_attrs(_values=is_mapping(query.args._values)),
        )

    elif isinstance(query, schema.ListQuery):
        return has_attrs(
            type=query.type,
            element_query=is_query(query.element_query),
        )

    elif isinstance(query, schema.NullableQuery):
        return has_attrs(
            type=query.type,
            element_query=is_query(query.element_query),
        )

    elif isinstance(query, schema.ObjectQuery):
        return has_attrs(
            type=query.type,
            field_queries=is_sequence(*[
                is_query(field_query)
                for field_query in query.field_queries
            ]),
        )

    else:
        raise Exception("Unhandled query type: {}".format(type(query)))
