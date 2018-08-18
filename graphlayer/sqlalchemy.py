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
        return expand(
            graph,
            query=query,
            where=where,
            extra_expressions=[],
            process_row=lambda row, result: result,
        )
    
    @g.expander(g.ListType(type), "indexed_object_representation", dict(
        query=g.object_query,
        where="where",
        index_expressions="index_expressions",
    ))
    def expand_indexed_objects(graph, query, where, index_expressions):
        return iterables.to_dict(expand(
            graph,
            query=query,
            where=where,
            extra_expressions=index_expressions,
            process_row=lambda row, result: (tuple(row), result),
        ))
        
    def expand(graph, query, where, extra_expressions, process_row):
        query_expressions = []
        
        base_query = sqlalchemy.orm.Query([]).select_from(model)
            
        if where is not None:
            base_query = base_query.filter(where)
        
        join_results = {}
        
        for key, field_query in query.element_query.fields.items():
            if field_query.field in expressions:
                query_expressions.append(expressions[field_query.field].label(key))
            else:
                join = joins[field_query.field]
                for index, local_key_expression in enumerate(join.keys()):
                    query_expressions.append(local_key_expression)
                if len(join) == 1:
                    foreign_key_expression, = join.values()
                else:
                    foreign_key_expression = sqlalchemy.tuple_(*join.values())
                
                where = foreign_key_expression.in_(base_query.add_columns(*join.keys()))
                
                join_results[key] = graph.expand(
                    g.ListType(field_query.field.type),
                    "indexed_object_representation",
                    {
                        g.object_query: ListQuery(field_query.field.type, field_query.type_query),
                        "where": where,
                        "index_expressions": join.values(),
                    },
                )
        
        def create_field_reader(key, field_query):
            if field_query.field in expressions:
                return lambda row: row.pop()
            else:
                join = joins[field_query.field]
                results = join_results[key]
                join_range = range(len(join))
                return lambda row: results[tuple([
                    row.pop()
                    for _ in join_range
                ])]
        
        readers = [
            (key, create_field_reader(key, field_query))
            for key, field_query in query.element_query.fields.items()
        ]
        
        def read_row(row):
            row = list(row)
            return process_row(
                row,
                g.ObjectResult(iterables.to_dict(
                    (key, read(row))
                    for key, read in readers
                ))
            )
        
        return [
            read_row(row)
            for row in base_query.with_session(session).add_columns(*extra_expressions).add_columns(*reversed(query_expressions))
        ]
        
    return [expand_objects, expand_indexed_objects]
