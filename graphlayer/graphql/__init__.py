import graphql
from graphql.execution import execute as graphql_execute
from graphql.language.parser import parse as graphql_parse
from graphql.validation import validate as graphql_validate

from . import parser
from .schema import to_graphql_type


def execute(*, graph, query_type, mutation_type=None, document_text, variables=None):
    graphql_schema = _create_graphql_schema(query_type=query_type, mutation_type=mutation_type)
    graphql_document_ast = graphql_parse(document_text)
    graphql_validation_errors = graphql_validate(graphql_schema, graphql_document_ast)
    if graphql_validation_errors:
        raise(graphql_validation_errors[0])
    
    query = parser.document_text_to_query(
        document_text=document_text,
        query_type=query_type,
        mutation_type=mutation_type,
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


def _create_graphql_schema(query_type, mutation_type):
    graphql_query_type = to_graphql_type(query_type).of_type
    if mutation_type is None:
        graphql_mutation_type = None
    else:
        graphql_mutation_type = to_graphql_type(query_type).of_type
        
    return graphql.GraphQLSchema(
        query=graphql_query_type,
        mutation=graphql_mutation_type,
    ) 


def _execute_graphql_schema(graphql_schema_document, graphql_schema):
    # TODO: handle errors
    return graphql_execute(
        graphql_schema,
        graphql_schema_document,
        # TODO: variables
        variable_values={},
    ).data
