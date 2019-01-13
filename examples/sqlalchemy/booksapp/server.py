import os

import flask
from graphlayer.graphql import execute as graphql_execute
import sqlalchemy.orm

from . import database
from .graph import create_graph, Root


def local_path(path):
    return os.path.join(os.path.dirname(__file__), "..", path)


app = flask.Flask(__name__, static_folder=local_path("static"))


@app.route("/")
def graphiql():
    with open(local_path("graphiql/index.html"), encoding="utf-8") as fileobj:
        return fileobj.read()


@app.route("/graphql", methods=["POST"])
def graphql():
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    database.setup(engine=engine)

    request = flask.request.get_json()
    query = request["query"]
    variables = request.get("variables") or {}

    session = sqlalchemy.orm.Session(engine)
    try:
        response = graphql_execute(
            graph=create_graph(session=session),
            document_text=query,
            variables=variables,
            query_type=Root,
        )
    finally:
        session.close()

    return flask.jsonify({"data": response})
