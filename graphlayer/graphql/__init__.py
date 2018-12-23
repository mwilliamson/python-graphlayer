from . import parser


def execute(*, graph, query_type, mutation_type=None, document_text, variables=None):
    query = parser.document_text_to_query(
        document_text=document_text,
        query_type=query_type,
        mutation_type=mutation_type,
        variables=variables,
    )
    
    result = graph.resolve(query)
    
    return query.to_json_value(result)
