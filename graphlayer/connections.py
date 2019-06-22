import base64

import graphlayer as g
from graphlayer.core import Injector


def forward_connection(*, connection_type_name, node_type, select_by_cursor, fetch_cursors, cursor_encoding):
    Connection = g.ObjectType(
        connection_type_name,
        fields=lambda: (
            g.field("edges", type=g.ListType(Edge)),
            g.field("nodes", type=g.ListType(node_type)),
            g.field("page_info", type=PageInfo),
        ),
    )

    Edge = g.ObjectType(
        node_type.name + "Edge",
        fields=lambda: (
            g.field("cursor", type=g.String),
            g.field("node", type=node_type),
        ),
    )

    class ConnectionQuery(object):
        @staticmethod
        def select_field(query, *, args):
            if args.first < 0:
                raise g.GraphError("first must be non-negative integer, was {}".format(args.first))
            else:
                return ConnectionQuery(type_query=query, first=args.first, after=args.after)

        def __init__(self, *, type_query, first, after):
            self.type = ConnectionQuery
            self.type_query = type_query
            self.first = first
            self.after = after

    @g.dependencies(injector=Injector)
    @g.resolver(ConnectionQuery)
    def resolve_connection(graph, query, *, injector):
        build_connection = g.create_object_builder(query.type_query)

        if query.after is None:
            after_cursor = None
        else:
            after_cursor = cursor_encoding.decode(query.after)

        edge_cursors = injector.call_with_dependencies(fetch_cursors, after_cursor=after_cursor, limit=query.first + 1)
        if len(edge_cursors) > query.first:
            edge_cursors = edge_cursors[:-1]
            has_next_page = True
        else:
            has_next_page = False

        @build_connection.field(Connection.fields.edges)
        def field_edges(field_query):
            build_edge = g.create_object_builder(field_query.type_query.element_query)

            @build_edge.getter(Edge.fields.cursor)
            def field_cursor(cursor):
                return cursor_encoding.encode(cursor)

            @build_edge.field(Edge.fields.node)
            def field_node(field_query):
                edges = graph.resolve(
                    select_by_cursor(field_query.type_query, edge_cursors)
                )

                return lambda edge_cursor: edges[edge_cursor]

            return lambda _: [
                build_edge(edge_cursor)
                for edge_cursor in edge_cursors
            ]

        @build_connection.field(Connection.fields.nodes)
        def field_nodes(field_query):
            nodes = graph.resolve(
                select_by_cursor(field_query.type_query.element_query, edge_cursors)
            )

            result = [nodes[edge_cursor] for edge_cursor in edge_cursors]

            return lambda _: result

        @build_connection.field(Connection.fields.page_info)
        def field_page_info(field_query):
            build_page_info = g.create_object_builder(field_query.type_query)

            @build_page_info.getter(PageInfo.fields.has_next_page)
            def field_has_next_page(_):
                return has_next_page

            @build_page_info.getter(PageInfo.fields.end_cursor)
            def field_end_cursor(_):
                if edge_cursors:
                    return cursor_encoding.encode(edge_cursors[-1])
                else:
                    return None

            return lambda _: build_page_info(None)

        return build_connection(None)

    return ForwardConnection(
        Connection=Connection,
        Edge=Edge,
        resolver=resolve_connection,
        select_field=ConnectionQuery.select_field,
    )


class ForwardConnection(object):
    def __init__(self, Connection, Edge, resolver, select_field):
        self.Connection = Connection
        self.Edge = Edge
        self.resolvers = (resolver, )
        self.select_field = select_field

    def field(self, field_name):
        return g.field(field_name, type=self.Connection, params=(
            g.param("after", type=g.NullableType(g.String), default=None),
            g.param("first", type=g.Int),
        ))


PageInfo = g.ObjectType(
    "PageInfo",
    fields=lambda: (
        g.field("end_cursor", type=g.NullableType(g.String)),
        g.field("has_next_page", type=g.Boolean),
    ),
)


class int_cursor_encoding(object):
    @staticmethod
    def encode(cursor):
        return base64.b64encode(str(cursor).encode("ascii")).decode("ascii")

    @staticmethod
    def decode(cursor):
        return int(base64.b64decode(cursor.encode("ascii")).decode("ascii"))

