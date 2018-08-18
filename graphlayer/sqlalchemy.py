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
        primary_key_query="primary_key_query",
    ))
    def expand_objects(graph, query, primary_key_query):
        primary_keys = primary_key_query.subquery()
        
        primary_key_expression, = model.__mapper__.primary_key
        
        base_query = sqlalchemy.orm.Query([]) \
            .select_from(model) \
            .filter(primary_key_expression.in_(primary_keys))
        
        sql_query = base_query
        
        join_results = {}
        
        for key, field_query in query.element_query.fields.items():
            if field_query.field in expressions:
                sql_query = sql_query.add_columns(expressions[field_query.field].label(key))
            else:
                expression = joins[field_query.field]
                sql_query = sql_query.add_columns(expression.label(key))
                join_results[key] = graph.expand(
                    g.ListType(field_query.field.type),
                    "indexed_object_representation",
                    {
                        g.object_query: ListQuery(field_query.field.type, field_query.type_query),
                        "primary_key_query": base_query.add_columns(expression),
                    },
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
            for row in sql_query.with_session(session)
        ]
    
    @g.expander(g.ListType(type), "indexed_object_representation", dict(
        query=g.object_query,
        primary_key_query="primary_key_query",
    ))
    def expand_indexed_objects(graph, query, primary_key_query):
        primary_keys = primary_key_query.subquery()
        
        primary_key_expression, = model.__mapper__.primary_key
        
        base_query = sqlalchemy.orm.Query([primary_key_expression.label("__primary_key")]) \
            .select_from(model) \
            .filter(primary_key_expression.in_(primary_keys))
        
        sql_query = base_query
        
        join_results = {}
        
        for key, field_query in query.element_query.fields.items():
            if field_query.field in expressions:
                sql_query = sql_query.add_columns(expressions[field_query.field].label(key))
            else:
                expression = joins[field_query.field]
                sql_query = sql_query.add_columns(expression.label("__join_{}".format(key)))
                join_results[key] = graph.expand(
                    g.ListType(field_query.field.type),
                    "indexed_object_representation",
                    {
                        g.object_query: ListQuery(field_query.field.type, field_query.type_query),
                        "primary_key_query": base_query.add_columns(expression),
                    },
                )
        
        def read_field(row, key):
            if key in row:
                return row[key]
            else:
                return join_results[key]
        
        return iterables.to_dict([
            (
                row.__primary_key,
                g.ObjectResult(iterables.to_dict(
                    (key, read_field(row._asdict(), key))
                    for key, field_query in query.element_query.fields.items()
                ))
            )
            for row in sql_query.with_session(session)
        ])
        
    return [expand_objects, expand_indexed_objects]
