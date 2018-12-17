import re

from graphql.language import ast as graphql_ast, parser as graphql_parser

from .iterables import find, to_dict


def document_text_to_query(document_text, query_type):
    document_ast = graphql_parser.parse(document_text)
    operation = find(
        lambda operation: isinstance(operation, graphql_ast.OperationDefinition),
        document_ast.definitions,
    )
    fields = _read_selection_set(operation.selection_set, type=query_type)
    return query_type(**fields)


def _read_selection_set(selection_set, type):
    if selection_set is None:
        return {}
    else:
        return to_dict(
            _read_selection(selection, type=type)
            for selection in selection_set.selections
        )


def _read_selection(selection, type):
    key = _field_key(selection)
    field_name = _camel_case_to_snake_case(selection.name.value)
    field = getattr(type, field_name)
    subfields = _read_selection_set(selection.selection_set, type=field.type)
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
