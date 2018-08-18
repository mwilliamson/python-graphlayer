from __future__ import absolute_import

import sqlalchemy.orm

import graphlayer as g
from . import iterables
from .schema import ListQuery


def sql_table_expander(type, model, session, expressions, joins=None):
    if joins is None:
        joins = {}
        
    @g.expander(g.ListType(type), g.object_representation, dict(
        query=g.object_query,
        where="where",
    ))
    def expand_objects(graph, query, where):
        rows, join_results = expand(
            graph,
            query=query,
            where=where,
            extra_expressions=[],
        )
        
        def read_field(row, key, field_query):
            if field_query.field in expressions:
                return row[key]
            else:
                return join_results[key][row[key]]
        
        return [
            g.ObjectResult(iterables.to_dict(
                (key, read_field(row._asdict(), key, field_query))
                for key, field_query in query.element_query.fields.items()
            ))
            for row in rows
        ]
    
    @g.expander(g.ListType(type), "indexed_object_representation", dict(
        query=g.object_query,
        where="where",
        index_expression="index_expression",
    ))
    def expand_indexed_objects(graph, query, where, index_expression):
        rows, join_results = expand(
            graph,
            query=query,
            where=where,
            extra_expressions=[index_expression.label("__index")],
        )
        
        def read_field(row, key):
            if key in row:
                return row[key]
            else:
                return join_results[key]
        
        return iterables.to_dict([
            (
                row.__index,
                g.ObjectResult(iterables.to_dict(
                    (key, read_field(row._asdict(), key))
                    for key, field_query in query.element_query.fields.items()
                ))
            )
            for row in rows
        ])
    
    def expand(graph, query, where, extra_expressions):
        base_query = sqlalchemy.orm.Query(extra_expressions) \
            .select_from(model)
            
        if where is not None:
            base_query = base_query.filter(where)
        
        sql_query = base_query
        
        join_results = {}
        
        for key, field_query in query.element_query.fields.items():
            if field_query.field in expressions:
                sql_query = sql_query.add_columns(expressions[field_query.field].label(key))
            else:
                # TODO: support multiple join keys
                (local_expression, foreign_expression), = joins[field_query.field].items()
                sql_query = sql_query.add_columns(local_expression.label(key))
                join_results[key] = graph.expand(
                    g.ListType(field_query.field.type),
                    "indexed_object_representation",
                    {
                        g.object_query: ListQuery(field_query.field.type, field_query.type_query),
                        "where": foreign_expression.in_(base_query.add_columns(local_expression)),
                        "index_expression": foreign_expression,
                    },
                )
        
        return sql_query.with_session(session), join_results
        
    return [expand_objects, expand_indexed_objects]
