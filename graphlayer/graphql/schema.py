from .. import schema

import graphql


def to_graphql_type(graph_type):
    if graph_type == schema.Boolean:
        return graphql.GraphQLNonNull(graphql.GraphQLBoolean)
    elif graph_type == schema.Float:
        return graphql.GraphQLNonNull(graphql.GraphQLFloat)
    elif graph_type == schema.Int:
        return graphql.GraphQLNonNull(graphql.GraphQLInt)
    elif graph_type == schema.String:
        return graphql.GraphQLNonNull(graphql.GraphQLString)
    
    elif isinstance(graph_type, schema.ListType):
        return graphql.GraphQLList(to_graphql_type(graph_type.element_type))
    
    elif isinstance(graph_type, schema.NullableType):
        return to_graphql_type(graph_type.element_type).of_type
    
    else:
        raise ValueError("unsupported type: {}".format(graph_type))
