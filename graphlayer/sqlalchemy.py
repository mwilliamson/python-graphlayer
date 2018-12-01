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
    
    def expressions(self):
        return (self._expression, )
    
    def create_reader(self, graph, field_query, base_query, session):
        def read(row):
            return row[0]
        
        return read


def sql_join(*args):
    if len(args) == 3:
        return _association_sql_join(*args)
    else:
        return _direct_sql_join(*args)


def _direct_sql_join(join):
    return lambda select_result: _DirectSqlJoinField(join, select_result=select_result)


class _DirectSqlJoinField(object):
    def __init__(self, join, select_result):
        self._join = join
        self._select_result = select_result
    
    def expressions(self):
        return self._join.keys()
    
    def create_reader(self, graph, field_query, base_query, session):
        foreign_key_expression = _to_sql_expression(self._join.values())
        where = foreign_key_expression.in_(base_query.add_columns(*self._join.keys()))
        
        list_query = _to_list_query(field_query)
        
        result = graph.expand(_IndexedQuery(
            type_query=list_query,
            where=where,
            index_expressions=self._join.values(),
        ))
            
        def read(row):
            return self._select_result(result.get(tuple(row), ()))
            
        return read


def _association_sql_join(left_join, association, right_join):
    return lambda select_result: _AssociationSqlJoinField(
        left_join=left_join,
        association=association,
        right_join=right_join,
        select_result=select_result,
    )


class _AssociationSqlJoinField(object):
    def __init__(self, left_join, association, right_join, select_result):
        self._left_join = left_join
        self._association = association
        self._right_join = right_join
        self._select_result = select_result
    
    def expressions(self):
        return self._left_join.keys()
    
    def create_reader(self, graph, field_query, base_query, session):
        base_association_query = sqlalchemy.orm.Query([]) \
            .select_from(self._association)
        
        association_query = base_association_query \
            .add_columns(*self._left_join.values()) \
            .add_columns(*self._right_join.keys())
        
        associations = [
            (row[:len(self._left_join)], row[len(self._left_join):])
            for row in association_query.with_session(session).all()
        ]
        
        foreign_key_expression = _to_sql_expression(self._right_join.values())
        where = foreign_key_expression.in_(base_association_query.add_columns(*self._right_join.keys()))
        
        list_query = _to_list_query(field_query)
        
        right_result = graph.expand(_IndexedQuery(
            type_query=list_query,
            where=where,
            index_expressions=self._right_join.values(),
        ))
        result = iterables.to_multidict(
            (left_key, right_value)
            for left_key, right_key in associations
            for right_value in right_result.get(right_key, ())
        )

        def read(row):
            return self._select_result(result.get(tuple(row), ()))
            
        return read


def _to_list_query(field_query):
    element_type = field_query.field.type
    type_query = field_query.type_query
    while isinstance(element_type, (g.ListType, g.NullableType)):
        element_type = element_type.element_type
        type_query = type_query.element_query
    
    return ListQuery(g.ListType(element_type), type_query)


def _to_sql_expression(expressions):
    if len(expressions) == 1:
        return expressions[0]
    else:
        return sqlalchemy.tuple_(*expressions)


def many(field):
    def select_result(values):
        return values

    return field(select_result=select_result)


def single(field):
    def select_result(values):
        if len(values) == 1:
            return values[0]
        else:
            raise ValueError("expected exactly one value")

    return field(select_result=select_result)


def single_or_null(field):
    def select_result(values):
        if len(values) == 0:
            return None
        elif len(values) == 1:
            return values[0]
        else:
            raise ValueError("expected zero or one values")

    return field(select_result=select_result)


_index_type_key = object()


def _index_type(t):
    return (_index_type_key, t)


class _IndexedQuery(object):
    def __init__(self, type_query, where, index_expressions):
        self.type = _index_type(type_query.type)
        self.type_query = type_query
        self.where = where
        self.index_expressions = index_expressions


def where(query, condition):
    return _FilteredQuery(type_query=query, where=condition)


_filtered_type_key = object()


def _filtered_type(t):
    return (_filtered_type_key, t)


class _FilteredQuery(object):
    def __init__(self, type_query, where):
        self.type = _filtered_type(type_query.type)
        self.type_query = type_query
        self.where = where


def sql_table_expander(type, model, fields, session):
    @g.expander(g.ListType(type))
    def expand_objects(graph, query):
        return graph.expand(_FilteredQuery(type_query=query, where=None))
        
    @g.expander(_filtered_type(g.ListType(type)))
    def expand_filtered_objects(graph, query):
        return expand(
            graph,
            query=query.type_query,
            where=query.where,
            extra_expressions=[],
            process_row=lambda row, result: result,
        )
    
    @g.expander(_index_type(g.ListType(type)))
    def expand_indexed_objects(graph, query):
        return iterables.to_multidict(expand(
            graph,
            query=query.type_query,
            where=query.where,
            extra_expressions=query.index_expressions,
            process_row=lambda row, result: (tuple(row), result),
        ))
        
    def expand(graph, query, where, extra_expressions, process_row):
        query_expressions = []
        
        base_query = sqlalchemy.orm.Query([]).select_from(model)
            
        if where is not None:
            base_query = base_query.filter(where)
        
        row_slices = []
        readers = []
        
        for field_query in query.element_query.fields.values():
            expressions = fields[field_query.field].expressions()
            row_slices.append(slice(len(query_expressions), len(query_expressions) + len(expressions))) 
            query_expressions += expressions
        
        rows = base_query.with_session(session).add_columns(*query_expressions).add_columns(*extra_expressions)
        
        for (key, field_query), row_slice in zip(query.element_query.fields.items(), row_slices):
            reader = fields[field_query.field].create_reader(graph, field_query, base_query, session=session)
            readers.append((key, row_slice, reader))
        
        def read_row(row):
            return process_row(
                row[len(query_expressions):],
                g.ObjectResult(iterables.to_dict(
                    (key, read(row[row_slice]))
                    for key, row_slice, read in readers
                ))
            )
        
        return [
            read_row(row)
            for row in rows
        ]
        
    return _Expander(expanders=[expand_objects, expand_filtered_objects, expand_indexed_objects])
    

class _Expander(object):
    def __init__(self, expanders):
        self.expanders = expanders
    
    def add(self, name):
        def add(value):
            setattr(self, name, value)
            return value
        
        return add
