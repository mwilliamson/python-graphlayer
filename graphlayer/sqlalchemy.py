import collections

import sqlalchemy.orm

import graphlayer as g
from . import iterables, schema
from .core import Injector
from .memo import memoize


def expression(expression):
    return _ExpressionField(expression)


class _ExpressionField(object):
    def __init__(self, expression):
        self._expression = expression

    def expressions(self):
        return (self._expression, )

    def create_reader(self, graph, field_query, base_query, injector):
        def read(row):
            return row[0]

        return read

    def map_value(self, func):
        return _DecoratedReadField(self, func)


def join(*, key, resolve):
    return _JoinField(key=_to_key(key), resolve=resolve)


def association_join(*, association_table, association_join, association_key, resolve):
    @g.dependencies(session=sqlalchemy.orm.Session)
    def _resolve(graph, field_query, foreign_key_sql_query, *, session):
        base_association_query = sqlalchemy.orm.Query([]) \
            .select_from(association_table) \
            .filter(_to_key(association_join.values()).expression().in_(foreign_key_sql_query))

        association_query = base_association_query \
            .add_columns(*association_join.values()) \
            .add_columns(*association_key)

        associations = [
            (row[:len(association_join)], row[len(association_join):])
            for row in association_query.with_session(session).all()
        ]

        right_result = resolve(graph, field_query, base_association_query.add_columns(*_to_key(association_key).expressions()))
        return _result_reader(field_query.type_query).read_results(
            (left_key, right_value)
            for left_key, right_key in associations
            for right_value in right_result[right_key]
        )

    return join(
        key=association_join.keys(),
        resolve=_resolve,
    )



def _to_key(key):
    if isinstance(key, collections.Iterable):
        return _MultipleExpressionKey(key)
    else:
        return _SingleExpressionKey(key)


class _SingleExpressionKey(object):
    def __init__(self, expression):
        self._expression = expression

    def expression(self):
        return self._expression

    def expressions(self):
        return (self._expression, )

    def read(self, row):
        return row[0]


class _MultipleExpressionKey(object):
    def __init__(self, expressions):
        self._expressions = expressions

    def expression(self):
        return sqlalchemy.tuple_(*self._expressions)

    def expressions(self):
        return self._expressions

    read = tuple


class _JoinField(object):
    def __init__(self, key, resolve):
        self._key = key
        self._resolve = resolve

    def expressions(self):
        return self._key.expressions()

    def create_reader(self, graph, field_query, base_query, injector):
        result = injector.call_with_dependencies(self._resolve, graph, field_query, base_query.add_columns(*self._key.expressions()))

        def read(row):
            return result[self._key.read(row)]

        return read


def sql_join(*args):
    if len(args) == 3:
        return _association_sql_join(*args)
    else:
        return _direct_sql_join(*args)


def _direct_sql_join(join_on):
    def resolve(graph, field_query, foreign_key_sql_query):
        sql_query = select(field_query.type_query).by(join_on.values(), foreign_key_sql_query)
        return graph.resolve(sql_query)

    return join(
        key=join_on.keys(),
        resolve=resolve,
    )


def _association_sql_join(left_join, association, right_join):
    def resolve(graph, field_query, foreign_key_sql_query):
        sql_query = select(field_query.type_query).by(right_join.values(), foreign_key_sql_query)
        return graph.resolve(sql_query)

    return association_join(
        association_table=association,
        association_join=left_join,
        association_key=right_join.keys(),
        resolve=resolve,
    )


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



class _SingleResultReader(object):
    def __init__(self, query):
        self.element_query = query

    def read_result(self, value):
        if len(value) == 1:
            return value[0]
        else:
            raise g.GraphError("expected exactly one value but got {}".format(len(value)))

    def read_results(self, iterable):
        result = {}

        for key, value in iterable:
            if key in result:
                raise g.GraphError("expected exactly one value")
            else:
                result[key] = value

        return result


class _ManyResultsReader(object):
    def __init__(self, query):
        self.element_query = query.element_query

    def read_result(self, value):
        return value

    def read_results(self, iterable):
        result = collections.defaultdict(list)

        for key, value in iterable:
            result[key].append(value)

        return result


class _SingleOrNullResultReader(object):
    def __init__(self, query):
        self.element_query = query.element_query

    def read_result(self, value):
        if len(value) == 0:
            return None
        elif len(value) == 1:
            return value[0]
        else:
            raise g.GraphError("expected exactly zero or one values but got {}".format(len(value)))

    def read_results(self, iterable):
        result = collections.defaultdict(lambda: None)

        for key, value in iterable:
            if key in result:
                raise g.GraphError("expected exactly zero or one values")
            else:
                result[key] = value

        return result


def _result_reader(query):
    if isinstance(query, schema.ObjectQuery):
        return _SingleResultReader(query)
    elif isinstance(query, schema.ListQuery) and isinstance(query.element_query, schema.ObjectQuery):
        return _ManyResultsReader(query)
    elif isinstance(query, schema.NullableQuery) and isinstance(query.element_query, schema.ObjectQuery):
        return _SingleOrNullResultReader(query)


def select(query):
    if isinstance(query, _SqlQuery):
        return query
    else:
        result_reader = _result_reader(query)

        return _SqlQuery(
            element_query=result_reader.element_query,
            read_result=result_reader.read_result,
            read_results=result_reader.read_results,
            index_key=None,
            where_clauses=(),
        )


_sql_query_type_key = object()


def _sql_query_type(t):
    return (_sql_query_type_key, t)


class _SqlQuery(object):
    def __init__(self, element_query, read_result, read_results, where_clauses, index_key):
        self.type = _sql_query_type(element_query.type)
        self.element_query = element_query
        self.read_result = read_result
        self.read_results = read_results
        self.where_clauses = where_clauses
        self.index_key = index_key

    def by(self, index_key, index_values):
        return self.index_by(index_key).where(_to_key(index_key).expression().in_(index_values))

    def index_by(self, index_key):
        return _SqlQuery(
            element_query=self.element_query,
            read_result=self.read_result,
            read_results=self.read_results,
            where_clauses=self.where_clauses,
            index_key=_to_key(index_key),
        )

    def where(self, where):
        return _SqlQuery(
            element_query=self.element_query,
            read_result=self.read_result,
            read_results=self.read_results,
            where_clauses=self.where_clauses + (where, ),
            index_key=self.index_key,
        )


def sql_table_resolver(type, model, fields):
    fields = memoize(fields)

    @g.resolver(_sql_query_type(type))
    @g.dependencies(injector=Injector, session=sqlalchemy.orm.Session)
    def resolve_sql_query(graph, query, *, injector, session):
        where = sqlalchemy.and_(*query.where_clauses)

        if query.index_key is None:
            return query.read_result(resolve(
                graph,
                query=query.element_query,
                where=where,
                extra_expressions=(),
                process_row=lambda row, result: result,
                session=session,
                injector=injector,
            ))
        else:
            return query.read_results(resolve(
                graph,
                query=query.element_query,
                where=where,
                extra_expressions=query.index_key.expressions(),
                process_row=lambda row, result: (query.index_key.read(row), result),
                session=session,
                injector=injector,
            ))

    def resolve(graph, query, where, extra_expressions, process_row, session, injector):
        def get_field(field_query):
            field = fields()[field_query.field]
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

        for field_query in query.field_queries:
            expressions = get_field(field_query).expressions()
            row_slices.append(slice(len(query_expressions), len(query_expressions) + len(expressions)))
            query_expressions += expressions

        rows = base_query.with_session(session).add_columns(*query_expressions).add_columns(*extra_expressions)

        for field_query, row_slice in zip(query.field_queries, row_slices):
            reader = get_field(field_query).create_reader(graph, field_query, base_query, injector=injector)
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
