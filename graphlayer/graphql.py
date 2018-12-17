from copy import copy
import re

from graphql.language import ast as graphql_ast, parser as graphql_parser

from .iterables import find, to_dict, to_multidict


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
        return [
            _read_graphql_field(graphql_field, graph_type=graph_type)
            for graphql_field in _flatten_graphql_selections(selection_set.selections)
        ]


def _flatten_graphql_selections(selections):
    # TODO: handle type conditions
    # TODO: validation
    graphql_fields = to_multidict(
        (_field_key(graphql_field), graphql_field)
        for selection in selections
        for graphql_field in _graphql_selection_to_graphql_fields(selection)
    )
    
    return [
        _merge_graphql_fields(graphql_fields_to_merge)
        for field_name, graphql_fields_to_merge in graphql_fields.items()
    ]


def _merge_graphql_fields(graphql_fields):
    merged_field = copy(graphql_fields[0])
    merged_field.selection_set = copy(merged_field.selection_set)
    
    for graphql_field in graphql_fields[1:]:
        merged_field.selection_set.selections += graphql_field.selection_set.selections
    
    return merged_field


def _graphql_selection_to_graphql_fields(selection):
    if isinstance(selection, graphql_ast.Field):
        return (selection, )
    
    elif isinstance(selection, graphql_ast.InlineFragment):
        return selection.selection_set.selections
        
    else:
        raise Exception("Unhandled selection type: {}".format(type(selection)))


def _read_graphql_field(graphql_field, graph_type):
    key = _field_key(graphql_field)
    field_name = _camel_case_to_snake_case(graphql_field.name.value)
    field = getattr(graph_type, field_name)
    subfields = to_dict(_read_selection_set(graphql_field.selection_set, graph_type=field.type))
    field_query = field(**subfields)
    return (key, field_query)


def _field_key(selection):
    if selection.alias is None:
        return selection.name.value
    else:
        return selection.alias.value


def _camel_case_to_snake_case(value):
    # From: https://stackoverflow.com/revisions/1176023/2
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
