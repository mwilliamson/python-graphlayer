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
            #~ extra_expressions=[index_expression.label("__index")],
            #~ process_row=lambda row, result: (row.__index, result),
            extra_expressions=index_expressions,
            process_row=lambda row, result: (row[:len(index_expressions)], result),
        ))
        
    def expand(graph, query, where, extra_expressions, process_row):
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
                join = joins[field_query.field]
                sql_query = sql_query.add_columns(*[
                    local_key_expression.label("{}_{}".format(key, index))
                    for index, local_key_expression in enumerate(join.keys())
                ])
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
        
        def read_field(row, key, field_query):
            if field_query.field in expressions:
                return getattr(row, key)
            else:
                join = joins[field_query.field]
                return join_results[key][tuple([
                    getattr(row, "{}_{}".format(key, index))
                    for index in range(len(join.keys()))
                ])]
        
        return [
            process_row(
                row,
                g.ObjectResult(iterables.to_dict(
                    (key, read_field(row, key, field_query))
                    for key, field_query in query.element_query.fields.items()
                ))
            )
            for row in sql_query.with_session(session)
        ]
        
    return [expand_objects, expand_indexed_objects]
