from precisely import equal_to, has_attrs, is_instance, is_mapping, is_sequence

from graphlayer import schema


def is_query(query):
    if query == schema.scalar_query:
        return equal_to(schema.scalar_query)
    
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
        
    elif isinstance(query, schema.ObjectQuery):
        return has_attrs(
            type=query.type,
            fields=is_sequence(*[
                is_query(field_query)
                for field_query in query.fields
            ]),
        )
    
    else:
        raise Exception("Unhandled query type: {}".format(type(query)))
