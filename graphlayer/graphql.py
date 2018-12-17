from graphql.language import ast as graphql_ast, parser as graphql_parser

from .iterables import find, to_dict


def document_text_to_query(document_text, query_type):
    document_ast = graphql_parser.parse(document_text)
    operation = find(
        lambda operation: isinstance(operation, graphql_ast.OperationDefinition),
        document_ast.definitions,
    )
    fields = to_dict(
        (_field_key(selection), getattr(query_type, selection.name.value)())
        for selection in operation.selection_set.selections
    )
    return query_type(**fields)


def _field_key(selection):
    if selection.alias is None:
        return selection.name.value
    else:
        return selection.alias.value
