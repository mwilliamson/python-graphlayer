from copy import copy
from functools import reduce
import re

from graphql.language import ast as graphql_ast, parser as graphql_parser
from graphql.validation import validate as graphql_validate

from .. import schema
from ..iterables import find, partition, to_dict
from .schema import create_graphql_schema


# TODO: validation
# TODO: type conditions on fragments


class GraphQLQuery(object):
    def __init__(self, graph_query, graphql_schema_document):
        self.graph_query = graph_query
        self.graphql_schema_document = graphql_schema_document


def document_text_to_query(document_text, query_type, mutation_type=None, variables=None):
    if variables is None:
        variables = {}

    document_ast = graphql_parser.parse(document_text)

    graphql_schema = create_graphql_schema(query_type=query_type, mutation_type=mutation_type)
    graphql_validation_errors = graphql_validate(graphql_schema, document_ast)
    if graphql_validation_errors:
        raise(graphql_validation_errors[0])

    operation_index, operation = find(
        lambda definition: isinstance(definition[1], graphql_ast.OperationDefinition),
        enumerate(document_ast.definitions),
    )

    if operation.operation == "query":
        root_type = query_type
    elif operation.operation == "mutation" and mutation_type is not None:
        root_type = mutation_type
    else:
        raise ValueError("unsupported operation: {}".format(operation.operation))

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
        graph_query = _read_selection_set(
            _copy_with(operation.selection_set, selections=non_schema_selections),
            graph_type=root_type,
            fragments=fragments,
            variables=variables,
        )
    else:
        graph_query=None

    return GraphQLQuery(
        graph_query,
        graphql_schema_document=schema_document,
    )


def _read_selection_set(selection_set, graph_type, fragments, variables):
    if selection_set is None:
        return graph_type()
    else:
        return reduce(
            lambda left, right: left + right,
            (
                _read_graphql_selection(
                    graphql_selection,
                    graph_type=graph_type,
                    fragments=fragments,
                    variables=variables,
                ).for_type(graph_type)
                for graphql_selection in selection_set.selections
            )
        )


def _read_graphql_selection(selection, graph_type, fragments, variables):
    if isinstance(selection, graphql_ast.Field):
        field = _read_graphql_field(selection, graph_type=graph_type, fragments=fragments, variables=variables)
        return graph_type(field)

    elif isinstance(selection, graphql_ast.InlineFragment):
        return _read_graphql_fragment(selection, graph_type=graph_type, fragments=fragments, variables=variables)

    elif isinstance(selection, graphql_ast.FragmentSpread):
        return _read_graphql_fragment(fragments[selection.name.value], graph_type=graph_type, fragments=fragments, variables=variables)

    else:
        raise Exception("Unhandled selection type: {}".format(type(selection)))


def _read_graphql_fragment(fragment, graph_type, fragments, variables):
    type_condition_type_name = fragment.type_condition.name.value

    if type_condition_type_name != graph_type.name and isinstance(graph_type, schema.InterfaceType):
        graph_type = find(lambda subtype: subtype.name == type_condition_type_name, graph_type.subtypes)

    return _read_selection_set(
        fragment.selection_set,
        graph_type=graph_type,
        fragments=fragments,
        variables=variables,
    )


def _read_graphql_field(graphql_field, graph_type, fragments, variables):
    key = _field_key(graphql_field)
    field_name = _camel_case_to_snake_case(graphql_field.name.value)
    field = _get_field(graph_type, field_name)

    def get_arg_value(arg):
        param = getattr(field.params, _camel_case_to_snake_case(arg.name.value))
        value = _read_value(arg.value, variables=variables, value_type=param.type)
        return param(value)

    args = [
        get_arg_value(arg)
        for arg in graphql_field.arguments
    ]
    type_query = _read_selection_set(
        graphql_field.selection_set,
        graph_type=field.type,
        fragments=fragments,
        variables=variables,
    )
    return field.query(key=key, args=args, type_query=type_query)


def _get_field(graph_type, field_name):
    while isinstance(graph_type, (schema.ListType, schema.NullableType)):
        graph_type = graph_type.element_type

    return getattr(graph_type.fields, field_name)


def _read_value(value, value_type, variables):
    if isinstance(value_type, schema.EnumType):
        raw_value = _read_value(value, schema.String, variables)
        enum_values = list(filter(
            lambda enum_value: enum_value.value == raw_value,
            value_type.enum,
        ))
        return enum_values[0]
    elif isinstance(value_type, schema.NullableType):
        return _read_value(value, value_type=value_type.element_type, variables=variables)
    elif isinstance(value, graphql_ast.BooleanValue):
        return value.value
    elif isinstance(value, graphql_ast.EnumValue):
        return value.value
    elif isinstance(value, graphql_ast.FloatValue):
        return float(value.value)
    elif isinstance(value, graphql_ast.IntValue):
        return int(value.value)
    elif isinstance(value, graphql_ast.ListValue):
        return [
            _read_value(element, variables=variables, value_type=value_type.element_type)
            for element in value.values
        ]
    elif isinstance(value, graphql_ast.ObjectValue):
        def get_field_value(field_input):
            field = getattr(value_type.fields, _camel_case_to_snake_case(field_input.name.value))
            return _read_value(field_input.value, variables=variables, value_type=field.type)

        return value_type(**to_dict(
            (_camel_case_to_snake_case(field_input.name.value), get_field_value(field_input))
            for field_input in value.fields
        ))
    elif isinstance(value, graphql_ast.StringValue):
        return value.value
    elif isinstance(value, graphql_ast.Variable):
        name = value.name.value
        return variables[name]
    else:
        raise ValueError("unhandled value: {}".format(type(value)))


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
