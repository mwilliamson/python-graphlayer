import sys

import graphlayer as g
from graphlayer import graphql

User = g.ObjectType("User", fields=(
    g.field("id", type=g.Int),
))

Query = g.ObjectType("Query", fields=(
    g.field("users", type=g.ListType(User)),
))

root_resolver = g.root_object_resolver(Query)

@root_resolver.field(Query.fields.users)
def root_resolve_users(graph, query, args):
    return graph.resolve(query)

@g.resolver(g.ListType(User))
def resolve_users(graph, query):
    return [
        query.element_query.create_object(dict(
            (field_query.key, getattr(user, field_query.field.name))
            for field_query in query.element_query.fields
        ))
        for user in users
    ]

resolvers = (root_resolver, resolve_users)

graph_definition = g.define_graph(resolvers=resolvers)
graph = graph_definition.create_graph({})

class UserRecord(object):
    def __init__(self, id):
        self.id = id

users = [UserRecord(index) for index in range(0, int(sys.argv[1]))]

print(graphql.execute(graph=graph, document_text='{ users { id } }', query_type=Query))


