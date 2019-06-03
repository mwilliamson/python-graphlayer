import graphql

from .. import iterables, schema
from .naming import snake_case_to_camel_case


class Schema(object):
    def __init__(self, query_type, mutation_type, types, graphql_schema):
        self.query_type = query_type
        self.mutation_type = mutation_type
        self.types = types
        self.graphql_schema = graphql_schema


def create_graphql_schema(query_type, mutation_type, types=None):
    if types is None:
        types = ()

    graphql_types = {}

    def to_graphql_type(graph_type):
        if graph_type not in graphql_types:
            graphql_types[graph_type] = generate_graphql_type(graph_type)

        return graphql_types[graph_type]

    def generate_graphql_type(graph_type):
        if graph_type == schema.Boolean:
            return graphql.GraphQLNonNull(graphql.GraphQLBoolean)
        elif graph_type == schema.Float:
            return graphql.GraphQLNonNull(graphql.GraphQLFloat)
        elif graph_type == schema.Int:
            return graphql.GraphQLNonNull(graphql.GraphQLInt)
        elif graph_type == schema.String:
            return graphql.GraphQLNonNull(graphql.GraphQLString)

        elif isinstance(graph_type, schema.EnumType):
            # TODO: should enums map names or values?
            values = iterables.to_dict(
                (member.value, graphql.GraphQLEnumValue(member.value))
                for member in graph_type.enum
            )
            graphql_type = graphql.GraphQLEnumType(graph_type.name, values=values)
            return graphql.GraphQLNonNull(graphql_type)

        elif isinstance(graph_type, schema.InputObjectType):
            return graphql.GraphQLNonNull(graphql.GraphQLInputObjectType(
                name=graph_type.name,
                fields=lambda: iterables.to_dict(
                    (snake_case_to_camel_case(field.name), to_graphql_input_field(field))
                    for field in graph_type.fields
                ),
            ))

        elif isinstance(graph_type, schema.InterfaceType):
            return graphql.GraphQLNonNull(graphql.GraphQLInterfaceType(
                name=graph_type.name,
                fields=to_graphql_fields(graph_type.fields),
                resolve_type=lambda: None,
            ))

        elif isinstance(graph_type, schema.ListType):
            return graphql.GraphQLNonNull(graphql.GraphQLList(to_graphql_type(graph_type.element_type)))

        elif isinstance(graph_type, schema.NullableType):
            return to_graphql_type(graph_type.element_type).of_type

        elif isinstance(graph_type, schema.ObjectType):
            return graphql.GraphQLNonNull(graphql.GraphQLObjectType(
                name=graph_type.name,
                fields=to_graphql_fields(graph_type.fields),
                interfaces=tuple(
                    to_graphql_type(interface).of_type
                    for interface in graph_type.interfaces
                ),
            ))

        else:
            raise ValueError("unsupported type: {}".format(graph_type))

    def to_graphql_input_field(graph_field):
        graphql_type = to_graphql_type(graph_field.type)

        if graph_field.has_default and isinstance(graphql_type, graphql.GraphQLNonNull):
            graphql_type = graphql_type.of_type

        return graphql.GraphQLInputField(type_=graphql_type)

    def to_graphql_fields(graph_fields):
        return lambda: iterables.to_dict(
            (snake_case_to_camel_case(field.name), to_graphql_field(field))
            for field in graph_fields
        )

    def to_graphql_field(graph_field):
        return graphql.GraphQLField(
            type_=to_graphql_type(graph_field.type),
            args=iterables.to_dict(
                (snake_case_to_camel_case(param.name), to_graphql_argument(param))
                for param in graph_field.params
            ),
        )

    def to_graphql_argument(param):
        graphql_type = to_graphql_type(param.type)

        if param.has_default and isinstance(graphql_type, graphql.GraphQLNonNull):
            graphql_type = graphql_type.of_type

        return graphql.GraphQLArgument(type_=graphql_type)

    graphql_query_type = to_graphql_type(query_type).of_type
    if mutation_type is None:
        graphql_mutation_type = None
    else:
        graphql_mutation_type = to_graphql_type(mutation_type).of_type

    for extra_type in types:
        to_graphql_type(extra_type)

    return Schema(
        query_type=query_type,
        mutation_type=mutation_type,
        types=types,
        graphql_schema=graphql.GraphQLSchema(
            query=graphql_query_type,
            mutation=graphql_mutation_type,
            types=tuple(graphql_types.values()),
        ),
    )
