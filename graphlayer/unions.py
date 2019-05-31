from . import core, schema


def select(query, select_elements, *, merge):
    return UnionQuery(
        type_query=query,
        select_elements=select_elements,
        merge=merge,
    )


class UnionQuery(object):
    def __init__(self, type_query, select_elements, merge):
        self.type = UnionQuery
        self.type_query = type_query
        self.select_elements = select_elements
        self.merge = merge


@core.resolver(UnionQuery)
def resolver(graph, query):
    return query.merge([
        graph.resolve(
            select_element(
                query.type_query.for_type(_replace_element_type(query.type_query.type, element_type)),
            ),
        )
        for element_type, select_element in query.select_elements
    ])


def _replace_element_type(graph_type, element_type):
    if isinstance(graph_type, schema.ListType):
        return schema.ListType(_replace_element_type(graph_type.element_type, element_type))
    elif isinstance(graph_type, schema.NullableType):
        return schema.NullableType(_replace_element_type(graph_type.element_type, element_type))
    else:
        return element_type
