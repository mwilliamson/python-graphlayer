from copy import copy
from functools import reduce
import re

from graphql import GraphQLError
from graphql.language import ast as graphql_ast, parser as graphql_parser
from graphql.validation import validate as graphql_validate

from .. import schema
from ..iterables import find, partition, to_dict


# TODO: validation


class GraphQLQuery(object):
    def __init__(self, graph_query, graphql_schema_document):
        self.graph_query = graph_query
        self.graphql_schema_document = graphql_schema_document


def document_text_to_query(document_text, graphql_schema, variables=None):
    if variables is None:
        variables = {}

    document_ast = graphql_parser.parse(document_text)

    graphql_validation_errors = graphql_validate(graphql_schema.graphql_schema, document_ast)
    if graphql_validation_errors:
        raise(graphql_validation_errors[0])

    operation_index, operation = find(
        lambda definition: isinstance(definition[1], graphql_ast.OperationDefinition),
        enumerate(document_ast.definitions),
    )

    if operation.operation == "query":
        root_type = graphql_schema.query_type
    elif operation.operation == "mutation" and graphql_schema.mutation_type is not None:
        root_type = graphql_schema.mutation_type
    else:
        raise GraphQLError(
            "unsupported operation: {}".format(operation.operation),
            nodes=(operation, ),
        )

    fragments = to_dict(
        (fragment.name.value, fragment)
        for fragment in filter(
            lambda definition: isinstance(definition, graphql_ast.FragmentDefinition),
            document_ast.definitions,
        )
    )

    # TODO: handle fragments with __schema
    schema_selections, non_schema_selections = partition(
        lambda selection: isinstance(selection, graphql_ast.Field) and selection.name.value == "__schema",
        operation.selection_set.selections,
    )

    if len(schema_selections) == 0:
        schema_document = None
    else:
        schema_operation = _copy_with(
            operation,
            selection_set=_copy_with(
                operation.selection_set,
                selections=schema_selections,
            ),
        )

        schema_definitions = copy(document_ast.definitions)
        schema_definitions[operation_index] = schema_operation

        schema_document = _copy_with(
            document_ast,
            definitions=schema_definitions,
        )

    if non_schema_selections:
        all_types = schema.collect_types((graphql_schema.query_type, graphql_schema.mutation_type) + tuple(graphql_schema.types))
        all_types_by_name = to_dict(
            (graph_type.name, graph_type)
            for graph_type in all_types
            if hasattr(graph_type, "name")
        )
        parser = Parser(fragments=fragments, types=all_types_by_name, variables=variables)
        graph_query = parser.read_selection_set(
            _copy_with(operation.selection_set, selections=non_schema_selections),
            graph_type=root_type,
        )
    else:
        graph_query=None

    return GraphQLQuery(
        graph_query,
        graphql_schema_document=schema_document,
    )


class Parser(object):
    def __init__(self, fragments, types, variables):
        self._fragments = fragments
        self._types = types
        self._variables = variables

    def read_selection_set(self, selection_set, graph_type):
        if selection_set is None:
            return graph_type()
        else:
            return reduce(
                lambda left, right: left + right,
                (
                    self._read_graphql_selection(
                        graphql_selection,
                        graph_type=graph_type,
                    )
                    for graphql_selection in selection_set.selections
                )
            )

    def _read_graphql_selection(self, selection, graph_type):
        if isinstance(selection, graphql_ast.Field):
            field = self._read_graphql_field(selection, graph_type=graph_type)
            return graph_type(field)

        elif isinstance(selection, graphql_ast.InlineFragment):
            return self._read_graphql_fragment(selection, graph_type=graph_type)

        elif isinstance(selection, graphql_ast.FragmentSpread):
            return self._read_graphql_fragment(self._fragments[selection.name.value], graph_type=graph_type)

        else:
            raise Exception("Unhandled selection type: {}".format(type(selection)))

    def _read_graphql_fragment(self, fragment, graph_type):
        type_condition_type_name = fragment.type_condition.name.value
        type_condition_type = self._find_type(type_condition_type_name)

        query = self.read_selection_set(
            fragment.selection_set,
            graph_type=type_condition_type,
        )

        return self._coerce_object_query(query, graph_type=graph_type)

    def _coerce_object_query(self, query, graph_type):
        return graph_type(*query.field_queries)

    def _read_graphql_field(self, graphql_field, graph_type):
        key = _field_key(graphql_field)
        field_name = _camel_case_to_snake_case(graphql_field.name.value)
        field = self._get_field(graph_type, field_name)

        def get_arg_value(arg):
            param = getattr(field.params, _camel_case_to_snake_case(arg.name.value))
            value = self._read_value_node(arg.value, value_type=param.type)
            return param(value)

        args = [
            get_arg_value(arg)
            for arg in graphql_field.arguments
        ]
        type_query = self.read_selection_set(
            graphql_field.selection_set,
            graph_type=field.type,
        )
        return field.query(key=key, args=args, type_query=type_query)

    def _get_field(self, graph_type, field_name):
        while isinstance(graph_type, (schema.ListType, schema.NullableType)):
            graph_type = graph_type.element_type

        return getattr(graph_type.fields, field_name)

    def _read_value_node(self, value, value_type):
        graphql_value = self._read_graphql_value(value)
        return self._convert_graphql_value(graphql_value, value_type=value_type)

    def _convert_graphql_value(self, graphql_value, value_type):
        if isinstance(value_type, schema.EnumType):
            enum_values = list(filter(
                lambda enum_value: enum_value.value == graphql_value,
                value_type.enum,
            ))
            return enum_values[0]

        elif isinstance(value_type, schema.NullableType):
            if graphql_value is None:
                return None
            else:
                return self._convert_graphql_value(graphql_value, value_type=value_type.element_type)

        elif value_type in (schema.Boolean, schema.Float, schema.Int, schema.String):
            return graphql_value

        elif isinstance(value_type, schema.ListType):
            return [
                self._convert_graphql_value(element, value_type=value_type.element_type)
                for element in graphql_value
            ]

        elif isinstance(value_type, schema.InputObjectType):
            def get_field_value(key, value):
                field = getattr(value_type.fields, _camel_case_to_snake_case(key))
                return self._convert_graphql_value(value, value_type=field.type)

            return value_type(**to_dict(
                (_camel_case_to_snake_case(key), get_field_value(key, value))
                for key, value in graphql_value.items()
            ))

        else:
            raise ValueError("unhandled type: {}".format(type(value_type)))

    def _read_graphql_value(self, value):
        if isinstance(value, graphql_ast.BooleanValue):
            return value.value
        elif isinstance(value, graphql_ast.EnumValue):
            return value.value
        elif isinstance(value, graphql_ast.FloatValue):
            return float(value.value)
        elif isinstance(value, graphql_ast.IntValue):
            return int(value.value)
        elif isinstance(value, graphql_ast.ListValue):
            return [
                self._read_graphql_value(element)
                for element in value.values
            ]
        elif isinstance(value, graphql_ast.ObjectValue):
            return to_dict(
                (field_input.name.value, self._read_graphql_value(field_input.value))
                for field_input in value.fields
            )
        elif isinstance(value, graphql_ast.StringValue):
            return value.value
        elif isinstance(value, graphql_ast.Variable):
            name = value.name.value
            return self._variables[name]
        else:
            raise ValueError("unhandled value: {}".format(type(value)))

    def _find_type(self, name):
        return self._types[name]


def _field_key(selection):
    if selection.alias is None:
        return selection.name.value
    else:
        return selection.alias.value


def _camel_case_to_snake_case(value):
    # From: https://stackoverflow.com/revisions/1176023/2
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def _copy_with(obj, **kwargs):
    result = copy(obj)
    for key, value in kwargs.items():
        setattr(result, key, value)
    return result
