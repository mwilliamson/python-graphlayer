import collections

import sqlalchemy.orm

import graphlayer as g
from . import iterables, schema


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

    def map_value(self, func):
        return _DecoratedReadField(self, func)


def sql_join(*args):
    if len(args) == 3:
        return _association_sql_join(*args)
    else:
        return _direct_sql_join(*args)


def _direct_sql_join(join):
    return _DirectSqlJoinField(join)


class _DirectSqlJoinField(object):
    def __init__(self, join):
        self._join = join

    def expressions(self):
        return self._join.keys()

    def create_reader(self, graph, field_query, base_query, session):
        foreign_key_expression = _to_sql_expression(self._join.values())
        where = foreign_key_expression.in_(base_query.add_columns(*self._join.keys()))

        sql_query = select(field_query.type_query) \
            .where(where) \
            .index_by(self._join.values())
        result = graph.resolve(sql_query)

        def read(row):
            return result[tuple(row)]

        return read


def _association_sql_join(left_join, association, right_join):
    return _AssociationSqlJoinField(
        left_join=left_join,
        association=association,
        right_join=right_join,
    )


class _AssociationSqlJoinField(object):
    def __init__(self, left_join, association, right_join):
        self._left_join = left_join
        self._association = association
        self._right_join = right_join

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

        sql_query = select(field_query.type_query) \
            .where(where) \
            .index_by(self._right_join.values())
        right_result = graph.resolve(sql_query)
        result = sql_query.read_results(
            (left_key, right_value)
            for left_key, right_key in associations
            for right_value in right_result[right_key]
        )

        def read(row):
            return result[tuple(row)]

        return read


def _to_sql_expression(expressions):
    if len(expressions) == 1:
        return next(iter(expressions))
    else:
        return sqlalchemy.tuple_(*expressions)


class _DecoratedReadField(object):
    def __init__(self, field, func):
        self._field = field
        self._func = func

    def expressions(self):
        return self._field.expressions()

    def create_reader(self, *args, **kwargs):
        read_many = self._field.create_reader(*args, **kwargs)

        def read(*args, **kwargs):
            return self._func(read_many(*args, **kwargs))

        return read


def select(query):
    if isinstance(query, _SqlQuery):
        return query
    else:
        if isinstance(query, schema.ObjectQuery):
            element_query = query

            def read_result(value):
                if len(value) == 1:
                    return value[0]
                else:
                    raise ValueError("expected exactly one value")

            def read_results(iterable):
                result = {}

                for key, value in iterable:
                    if key in result:
                        raise ValueError("expected exactly one value")
                    else:
                        result[key] = value

                return result

        elif isinstance(query, schema.ListQuery) and isinstance(query.element_query, schema.ObjectQuery):
            element_query = query.element_query

            def read_result(value):
                return value

            def read_results(iterable):
                result = collections.defaultdict(list)

                for key, value in iterable:
                    result[key].append(value)

                return result

        elif isinstance(query, schema.NullableQuery) and isinstance(query.element_query, schema.ObjectQuery):
            element_query = query.element_query

            def read_result(value):
                if len(value) == 0:
                    return None
                elif len(value) == 1:
                    return value[0]
                else:
                    raise ValueError("expected exactly zero or one values")

            def read_results(iterable):
                result = collections.defaultdict(lambda: None)

                for key, value in iterable:
                    if key in result:
                        raise ValueError("expected exactly zero or one values")
                    else:
                        result[key] = value

                return result

        return _SqlQuery(
            element_query=element_query,
            read_result=read_result,
            read_results=read_results,
            index_expressions=None,
            where_clauses=(),
        )


_sql_query_type_key = object()


def _sql_query_type(t):
    return (_sql_query_type_key, t)


class _SqlQuery(object):
    def __init__(self, element_query, read_result, read_results, where_clauses, index_expressions):
        self.type = _sql_query_type(element_query.type)
        self.element_query = element_query
        self.read_result = read_result
        self.read_results = read_results
        self.where_clauses = where_clauses
        self.index_expressions = index_expressions

    def index_by(self, index_expressions):
        return _SqlQuery(
            element_query=self.element_query,
            read_result=self.read_result,
            read_results=self.read_results,
            where_clauses=self.where_clauses,
            index_expressions=index_expressions,
        )

    def where(self, where):
        return _SqlQuery(
            element_query=self.element_query,
            read_result=self.read_result,
            read_results=self.read_results,
            where_clauses=self.where_clauses + (where, ),
            index_expressions=self.index_expressions,
        )


def sql_table_resolver(type, model, fields):
    @g.resolver(_sql_query_type(type))
    @g.dependencies(session=sqlalchemy.orm.Session)
    def resolve_sql_query(graph, query, session):
        where = sqlalchemy.and_(*query.where_clauses)

        if query.index_expressions is None:
            return query.read_result(resolve(
                graph,
                query=query.element_query,
                where=where,
                extra_expressions=(),
                process_row=lambda row, result: result,
                session=session,
            ))
        else:
            return query.read_results(resolve(
                graph,
                query=query.element_query,
                where=where,
                extra_expressions=query.index_expressions,
                process_row=lambda row, result: (tuple(row), result),
                session=session,
            ))

    def resolve(graph, query, where, extra_expressions, process_row, session):
        def get_field(field_query):
            field = fields[field_query.field]
            if callable(field):
                return field(field_query.args)
            else:
                return field

        query_expressions = []

        base_query = sqlalchemy.orm.Query([]).select_from(model)

        if where is not None:
            base_query = base_query.filter(where)

        row_slices = []
        readers = []

        for field_query in query.fields:
            expressions = get_field(field_query).expressions()
            row_slices.append(slice(len(query_expressions), len(query_expressions) + len(expressions)))
            query_expressions += expressions

        rows = base_query.with_session(session).add_columns(*query_expressions).add_columns(*extra_expressions)

        for field_query, row_slice in zip(query.fields, row_slices):
            reader = get_field(field_query).create_reader(graph, field_query, base_query, session=session)
            readers.append((field_query.key, row_slice, reader))

        def read_row(row):
            return process_row(
                row[len(query_expressions):],
                query.create_object(iterables.to_dict(
                    (key, read(row[row_slice]))
                    for key, row_slice, read in readers
                ))
            )

        return [
            read_row(row)
            for row in rows
        ]

    return resolve_sql_query
