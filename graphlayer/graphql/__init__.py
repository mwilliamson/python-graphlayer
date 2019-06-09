from graphql import GraphQLError
from graphql.execution import execute as graphql_execute, ExecutionResult

from .. import GraphError
from . import parser
from .schema import create_graphql_schema


def execute(document_text, *, graph, query_type, mutation_type=None, types=None, variables=None):
    return executor(
        query_type=query_type,
        mutation_type=mutation_type,
        types=types,
    )(document_text, graph=graph, variables=variables)


def executor(*, query_type, mutation_type=None, types=None):
    graphql_schema = create_graphql_schema(query_type=query_type, mutation_type=mutation_type, types=types)

    def execute(document_text, *, graph, variables=None):
        try:
            query = parser.document_text_to_query(
                document_text=document_text,
                variables=variables,
                graphql_schema=graphql_schema,
            )

            if query.graph_query is None:
                result = {}
            else:
                result = graph.resolve(query.graph_query)

            if query.graphql_schema_document is not None:
                schema_result = _execute_graphql_schema(
                    graphql_schema_document=query.graphql_schema_document,
                    graphql_schema=graphql_schema.graphql_schema,
                    variables=query.variables,
                )
                result = result.copy()
                result.update(schema_result)

            return ExecutionResult(
                data=result,
                errors=None,
            )
        except (GraphQLError, GraphError) as error:
            return ExecutionResult(
                data=None,
                errors=[error],
            )

    return execute


def _execute_graphql_schema(graphql_schema_document, graphql_schema, variables):
    # TODO: handle errors
    result = graphql_execute(
        graphql_schema,
        graphql_schema_document,
        # TODO: variables
        variable_values=variables,
    )
    if result.errors:
        raise result.errors[0]
    else:
        return result.data
