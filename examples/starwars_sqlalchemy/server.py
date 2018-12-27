import os

import flask

import graphlayer as g
from graphlayer.graphql import execute as graphql_execute

app = flask.Flask(__name__)

Root = g.ObjectType("Root", fields=(
    g.field("value", g.Int),
))

root_resolver = g.root_object_resolver(Root)

@root_resolver.field(Root.fields.value)
def root_resolve_value(graph, query, args):
    return 42

resolvers = (root_resolver, )

graph_definition = g.define_graph(resolvers=resolvers)
graph = graph_definition.create_graph({})

@app.route("/")
def graphiql():
    with open(os.path.join(os.path.dirname(__file__), "graphiql/index.html"), encoding="utf-8") as fileobj:
        return fileobj.read()

@app.route("/graphql", methods=["POST"])
def graphql():
    request = flask.request.get_json()
    query = request["query"]
    variables = request.get("variables") or {}
    
    response = graphql_execute(
        graph=graph,
        document_text=query,
        variables=variables,
        query_type=Root,
    )
    
    return flask.jsonify({"data": response})
