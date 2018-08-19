from __future__ import absolute_import

import sqlalchemy.orm

import graphlayer as g
from . import iterables
from .schema import ListQuery


def expression(expression):
    return _ExpressionField(expression)


class _ExpressionField(object):
    def __init__(self, expression):
        self._expression = expression
    
    def process(self, graph, field_query, base_query):
        return ((self._expression, ), None)
    
    def create_reader(self, result):
        def read(row):
            return row.pop()
        
        return read


def sql_join(join):
    return _SqlJoinField(join)


class _SqlJoinField(object):
    def __init__(self, join):
        self._join = join
    
    def process(self, graph, field_query, base_query):
        if len(self._join) == 1:
            foreign_key_expression, = self._join.values()
        else:
            foreign_key_expression = sqlalchemy.tuple_(*self._join.values())
        
        where = foreign_key_expression.in_(base_query.add_columns(*self._join.keys()))
        
        element_type = field_query.field.type
        type_query = field_query.type_query
        while isinstance(element_type, (g.ListType, g.NullableType)):
            element_type = element_type.element_type
            type_query = type_query.element_query
        
        result = graph.expand(
            g.ListType(element_type),
            "indexed_object_representation",
            {
                g.object_query: ListQuery(g.ListType(element_type), type_query),
                "where": where,
                "index_expressions": self._join.values(),
            },
        )
        return self._join.keys(), result
    
    def create_reader(self, result):
        join_range = range(len(self._join))
        
        def read(row):
            return result.get(tuple([
                row.pop()
                for _ in join_range
            ]))
            
        return read


def sql_table_expander(type, model, fields, session):
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
            expressions, result = fields[field_query.field].process(graph, field_query, base_query)
            query_expressions += expressions
            join_results[key] = result
        
        def create_field_reader(key, field_query):
            return fields[field_query.field].create_reader(join_results[key])
        
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
    
