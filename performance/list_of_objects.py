import sys
import time


class UserRecord(object):
    def __init__(self, id, name):
        self.id = id
        self.name = name


users = [
    UserRecord(id=index, name="user{}".format(index))
    for index in range(0, int(sys.argv[1]))
]


def graphlayer_performance():
    import graphlayer as g
    from graphlayer import graphql

    User = g.ObjectType(
        "User",
        fields=(
            g.field("id", type=g.Int),
            g.field("name", type=g.String),
        ),
    )

    Query = g.ObjectType("Query", fields=(g.field("users", type=g.ListType(User)),))

    root_resolver = g.root_object_resolver(Query)

    @root_resolver.field(Query.fields.users)
    def root_resolve_users(graph, query, args):
        return graph.resolve(query)

    @g.resolver(g.ListType(User))
    def resolve_users(graph, query):
        return [
            query.element_query.create_object(
                dict(
                    (field_query.key, getattr(user, field_query.field.name))
                    for field_query in query.element_query.field_queries
                )
            )
            for user in users
        ]

    resolvers = (root_resolver, resolve_users)

    graph_definition = g.define_graph(resolvers=resolvers)
    graph = graph_definition.create_graph({})
    return lambda document_text: graphql.execute(
        graph=graph, document_text=document_text, query_type=Query
    )


def graphql_performance():
    import graphql

    User = graphql.GraphQLObjectType(
        "User",
        fields={
            "id": graphql.GraphQLField(graphql.GraphQLNonNull(graphql.GraphQLInt)),
            "name": graphql.GraphQLField(graphql.GraphQLNonNull(graphql.GraphQLString)),
        },
    )

    Query = graphql.GraphQLObjectType(
        "Query",
        fields={
            "users": graphql.GraphQLField(
                graphql.GraphQLNonNull(
                    graphql.GraphQLList(graphql.GraphQLNonNull(User))
                ),
                resolve=lambda obj, info: users,
            ),
        },
    )

    schema = graphql.GraphQLSchema(
        query=Query,
    )

    return lambda document_text: graphql.graphql_sync(schema, document_text).data


for name, run_query in (
    ("graphql-core", graphql_performance()),
    ("graphlayer", graphlayer_performance()),
):
    start_time = time.time()
    run_query("{ users { id name } }")
    time_taken = time.time() - start_time
    print(name, time_taken)
