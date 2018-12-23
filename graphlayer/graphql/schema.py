from .. import iterables, schema

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
    
    elif isinstance(graph_type, schema.ObjectType):
        return graphql.GraphQLNonNull(graphql.GraphQLObjectType(
            name=graph_type.name,
            fields=iterables.to_dict(
                (field.name, to_graphql_field(field))
                for field in graph_type.fields
            ),
        ))
    
    else:
        raise ValueError("unsupported type: {}".format(graph_type))


def to_graphql_field(graph_field):
    return graphql.GraphQLField(type=to_graphql_type(graph_field.type))
