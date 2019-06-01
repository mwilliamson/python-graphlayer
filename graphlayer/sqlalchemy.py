import collections

import sqlalchemy.orm

import graphlayer as g
from . import iterables, schema
from .core import Injector
from .memo import memoize


def constant(value):
    return _ConstantField(expression)


class _ConstantField(object):
    def __init__(self, value):
        self._value = value

    def expressions(self):
        return ()

    def create_reader(self, base_query, field_query, injector):
        def read(row):
            return self._value

        return read


def expression(expression):
    return _ExpressionField(expression)


class _ExpressionField(object):
    def __init__(self, expression):
        self._expression = expression

    def expressions(self):
        return (self._expression, )

    def create_reader(self, base_query, field_query, injector):
        def read(row):
            return row[0]

        return read

    def map_value(self, func):
        return _DecoratedReadField(self, func)


def join(*, key, resolve, association=None):
    return _JoinField(key=_to_key(key), resolve=resolve, association=association)


class _Association(object):
    def __init__(self, table, left_key, right_key, distinct, filtered_by_left_key, order_by):
        self.table = table
        self.left_key = left_key
        self.right_key = right_key
        self.distinct = distinct
        self.filtered_by_left_key = filtered_by_left_key
        self.order_by = order_by


def association(table, *, left_key, right_key, distinct=False, filtered_by_left_key=False, order_by=None):
    return _Association(
        table=table,
        left_key=_to_key(left_key),
        right_key=_to_key(right_key),
        distinct=distinct,
        filtered_by_left_key=filtered_by_left_key,
        order_by=order_by,
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
    def __init__(self, key, resolve, association):
        self._key = key
        self._resolve = resolve
        self._association = association

    def expressions(self):
        return self._key.expressions()

    def create_reader(self, base_query, field_query, injector):
        key_sql_query = base_query.add_columns(*self._key.expressions())

        if self._association is None:
            result = injector.call_with_dependencies(self._resolve, key_sql_query)
        else:
            if callable(self._association):
                association = injector.call_with_dependencies(self._association, key_sql_query)
            else:
                association = self._association

            session = injector.get(sqlalchemy.orm.Session)

            if isinstance(association.table, sqlalchemy.orm.Query):
                base_association_query = association.table
            else:
                base_association_query = sqlalchemy.orm.Query([]) \
                    .select_from(association.table)

            if not association.filtered_by_left_key:
                base_association_query = base_association_query.filter(association.left_key.expression().in_(key_sql_query))

            association_query = base_association_query \
                .add_columns(*association.left_key.expressions()) \
                .add_columns(*association.right_key.expressions())

            if association.order_by is not None:
                association_query = association_query.order_by(association.order_by)

            if association.distinct:
                association_query = association_query.distinct()

            associations = [
                (
                    association.left_key.read(row[:len(association.left_key.expressions())]),
                    association.right_key.read(row[len(association.left_key.expressions()):]),
                )
                for row in association_query.with_session(session).all()
            ]

            right_result = injector.call_with_dependencies(self._resolve, base_association_query.add_columns(*association.right_key.expressions()))

            result = _result_reader(field_query.type_query).join_associations(associations, right_result)

        def read(row):
            return result[self._key.read(row)]

        return read


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

    def join_associations(self, associations, right_result):
        return self.read_results(
            (left_key, right_result[right_key])
            for left_key, right_key in associations
        )


class _ManyResultsReader(object):
    def __init__(self, query):
        self.element_query = query.element_query

    def read_result(self, value):
        return value

    def read_results(self, iterable):
        return iterables.to_default_multidict(iterable)

    def join_associations(self, associations, right_result):
        return self.read_results(
            (left_key, right_value)
            for left_key, right_key in associations
            for right_value in right_result[right_key]
        )


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

    def join_associations(self, associations, right_result):
        return self.read_results(
            (left_key, right_result[right_key])
            for left_key, right_key in associations
        )


def _result_reader(query):
    if isinstance(query, schema.ObjectQuery):
        return _SingleResultReader(query)
    elif isinstance(query, schema.ListQuery) and isinstance(query.element_query, schema.ObjectQuery):
        return _ManyResultsReader(query)
    elif isinstance(query, schema.NullableQuery) and isinstance(query.element_query, schema.ObjectQuery):
        return _SingleOrNullResultReader(query)


def _read_result(query, result):
    return _result_reader(query).read_result(result)


def _read_results(query, results):
    return _result_reader(query).read_results(results)


def select(query, tag=None):
    if isinstance(query, _SqlQuery):
        return query
    else:
        result_reader = _result_reader(query)
        element_query = result_reader.element_query

        if tag is None:
            tag = element_query.type

        type = _sql_query_type(tag)

        return _SqlQuery(
            type=type,
            element_query=element_query,
            type_query=query,
            index_key=None,
            where_clauses=(),
            order=None,
            limit=None,
        )


class _SqlQueryTypeKey(object):
    def __repr__(self):
        return __name__ + "." + select.__name__


_sql_query_type_key = _SqlQueryTypeKey()


def _sql_query_type(t):
    return (_sql_query_type_key, t)


class _SqlQuery(object):
    def __init__(self, type, element_query, type_query, where_clauses, index_key, order, limit):
        self.type = type
        self.element_query = element_query
        self.type_query = type_query
        self.where_clauses = where_clauses
        self.index_key = index_key
        self.order = order
        self.limit_ = limit

    def by(self, index_key, index_values):
        return self.index_by(index_key).where(_to_key(index_key).expression().in_(index_values))

    def index_by(self, index_key):
        return _SqlQuery(
            type=self.type,
            element_query=self.element_query,
            type_query=self.type_query,
            where_clauses=self.where_clauses,
            index_key=_to_key(index_key),
            order=self.order,
            limit=self.limit_,
        )

    def limit(self, limit):
        return _SqlQuery(
            type=self.type,
            element_query=self.element_query,
            type_query=self.type_query,
            where_clauses=self.where_clauses,
            index_key=self.index_key,
            order=self.order,
            limit=limit,
        )

    def order_by(self, *order):
        return _SqlQuery(
            type=self.type,
            element_query=self.element_query,
            type_query=self.type_query,
            where_clauses=self.where_clauses,
            index_key=self.index_key,
            order=order,
            limit=self.limit_,
        )

    def where(self, where):
        return _SqlQuery(
            type=self.type,
            element_query=self.element_query,
            type_query=self.type_query,
            where_clauses=self.where_clauses + (where, ),
            index_key=self.index_key,
            order=self.order,
            limit=self.limit_,
        )


def sql_table_resolver(type, model, fields):
    fields = memoize(fields)

    @g.resolver(_sql_query_type(type))
    @g.dependencies(injector=Injector, session=sqlalchemy.orm.Session)
    def resolve_sql_query(graph, query, *, injector, session):
        where = sqlalchemy.and_(*query.where_clauses)

        if query.index_key is None:
            return _read_result(query.type_query, resolve(
                graph,
                query=query.element_query,
                where=where,
                limit=query.limit_,
                order=query.order,
                extra_expressions=(),
                process_row=lambda row, result: result,
                session=session,
                injector=injector,
            ))
        else:
            return _read_results(query.type_query, resolve(
                graph,
                query=query.element_query,
                where=where,
                limit=query.limit_,
                order=query.order,
                extra_expressions=query.index_key.expressions(),
                process_row=lambda row, result: (query.index_key.read(row), result),
                session=session,
                injector=injector,
            ))

    def resolve(graph, query, where, limit, order, extra_expressions, process_row, session, injector):
        def get_field(field_query):
            if field_query.field == schema.typename_field and isinstance(query.type, schema.ObjectType):
                return _ConstantField(query.type.name)
            else:
                field = fields().get(field_query.field)
                if field is None:
                    raise g.GraphError("Resolver missing for field {}".format(field_query.field.name))
                elif callable(field):
                    # TODO: test dependencies are injected
                    return injector.call_with_dependencies(field, graph, field_query)
                else:
                    return field

        query_expressions = []

        base_query = sqlalchemy.orm.Query([]).select_from(model)

        if where is not None:
            base_query = base_query.filter(where)

        if order is not None:
            base_query = base_query.order_by(*order)

        if limit is not None:
            base_query = base_query.limit(limit)

        row_slices = []
        readers = []

        for field_query in query.field_queries:
            expressions = get_field(field_query).expressions()
            row_slices.append(slice(len(query_expressions), len(query_expressions) + len(expressions)))
            query_expressions += expressions

        row_query = base_query.add_columns(*query_expressions).add_columns(*extra_expressions)
        rows = row_query.with_session(session)

        for field_query, row_slice in zip(query.field_queries, row_slices):
            reader = get_field(field_query).create_reader(base_query, field_query=field_query, injector=injector)
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
