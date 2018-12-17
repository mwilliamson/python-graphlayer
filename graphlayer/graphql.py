import re

from graphql.language import ast as graphql_ast, parser as graphql_parser

from .iterables import find, to_dict


def document_text_to_query(document_text, query_type):
    document_ast = graphql_parser.parse(document_text)
    operation = find(
        lambda operation: isinstance(operation, graphql_ast.OperationDefinition),
        document_ast.definitions,
    )
    fields = to_dict(_read_selection_set(operation.selection_set, graph_type=query_type))
    return query_type(**fields)


def _read_selection_set(selection_set, graph_type):
    if selection_set is None:
        return ()
    else:
        return (
            (name, field_query)
            for selection in selection_set.selections
            for name, field_query in _read_selection(selection, graph_type=graph_type)
        )


def _read_selection(selection, graph_type):
    if isinstance(selection, graphql_ast.Field):
        return _read_field(selection, graph_type=graph_type)
    
    elif isinstance(selection, graphql_ast.InlineFragment):
        return _read_inline_fragment(selection, graph_type=graph_type)
        
    else:
        raise Exception("Unhandled selection type: {}".format(type(selection)))


def _read_field(graphql_field, graph_type):
    key = _field_key(graphql_field)
    field_name = _camel_case_to_snake_case(graphql_field.name.value)
    field = getattr(graph_type, field_name)
    subfields = to_dict(_read_selection_set(graphql_field.selection_set, graph_type=field.type))
    field_query = field(**subfields)
    return (
        (key, field_query),
    )


def _read_inline_fragment(fragment, graph_type):
    # TODO: handle type conditions
    return _read_selection_set(fragment.selection_set, graph_type=graph_type)


def _field_key(selection):
    if selection.alias is None:
        return selection.name.value
    else:
        return selection.alias.value


def _camel_case_to_snake_case(value):
    # From: https://stackoverflow.com/revisions/1176023/2
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
