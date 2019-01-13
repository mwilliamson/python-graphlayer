from graphql.execution import execute as graphql_execute

from . import parser
from .schema import create_graphql_schema


def execute(document_text, *, graph, query_type, mutation_type=None, types=None, variables=None):
    graphql_schema = create_graphql_schema(query_type=query_type, mutation_type=mutation_type, types=types)

    query = parser.document_text_to_query(
        document_text=document_text,
        query_type=query_type,
        mutation_type=mutation_type,
        types=types,
        variables=variables,
    )

    if query.graph_query is None:
        json_result = {}
    else:
        result = graph.resolve(query.graph_query)
        json_result = query.graph_query.to_json_value(result)

    if query.graphql_schema_document is not None:
        schema_result = _execute_graphql_schema(
            graphql_schema_document=query.graphql_schema_document,
            graphql_schema=graphql_schema,
        )
        json_result = json_result.copy()
        json_result.update(schema_result)

    return json_result


def _execute_graphql_schema(graphql_schema_document, graphql_schema):
    # TODO: handle errors
    return graphql_execute(
        graphql_schema,
        graphql_schema_document,
        # TODO: variables
        variable_values={},
    ).data
