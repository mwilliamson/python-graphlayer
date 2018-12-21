from copy import copy
import re

from graphql.language import ast as graphql_ast, parser as graphql_parser

from . import schema
from .iterables import find, to_dict, to_multidict
from .representations import Object


def document_text_to_query(document_text, query_type, mutation_type=None, variables=None):
    if variables is None:
        variables = {}
    
    document_ast = graphql_parser.parse(document_text)
    
    operation = find(
        lambda definition: isinstance(definition, graphql_ast.OperationDefinition),
        document_ast.definitions,
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
    
    fields = to_dict(_read_selection_set(
        operation.selection_set,
        graph_type=root_type,
        fragments=fragments,
        variables=variables,
    ))
    return root_type(**fields)


def _read_selection_set(selection_set, graph_type, fragments, variables):
    if selection_set is None:
        return ()
    else:
        return [
            _read_graphql_field(graphql_field, graph_type=graph_type, fragments=fragments, variables=variables)
            for graphql_field in _flatten_graphql_selections(selection_set.selections, fragments=fragments)
        ]


def _flatten_graphql_selections(selections, fragments):
    # TODO: handle type conditions
    # TODO: validation
    graphql_fields = to_multidict(
        (_field_key(graphql_field), graphql_field)
        for selection in selections
        for graphql_field in _graphql_selection_to_graphql_fields(selection, fragments=fragments)
    )
    
    return [
        _merge_graphql_fields(graphql_fields_to_merge)
        for field_name, graphql_fields_to_merge in graphql_fields.items()
    ]


def _merge_graphql_fields(graphql_fields):
    merged_field = copy(graphql_fields[0])
    merged_field.selection_set = copy(merged_field.selection_set)
    
    for graphql_field in graphql_fields[1:]:
        if graphql_field.selection_set is not None:
            merged_field.selection_set.selections += graphql_field.selection_set.selections
    
    return merged_field


def _graphql_selection_to_graphql_fields(selection, fragments):
    if isinstance(selection, graphql_ast.Field):
        return (selection, )
    
    elif isinstance(selection, graphql_ast.InlineFragment):
        return _graphql_fragment_to_graphql_fields(selection, fragments=fragments)
    
    elif isinstance(selection, graphql_ast.FragmentSpread):
        return _graphql_fragment_to_graphql_fields(fragments[selection.name.value], fragments=fragments)
        
    else:
        raise Exception("Unhandled selection type: {}".format(type(selection)))


def _graphql_fragment_to_graphql_fields(fragment, fragments):
    return [
        graphql_field
        for subselection in fragment.selection_set.selections
        for graphql_field in _graphql_selection_to_graphql_fields(subselection, fragments=fragments)
    ]


def _read_graphql_field(graphql_field, graph_type, fragments, variables):
    key = _field_key(graphql_field)
    field_name = _camel_case_to_snake_case(graphql_field.name.value)
    field = _get_field(graph_type, field_name)
    args = [
        getattr(field.params, arg.name.value)(_read_value(arg.value, variables=variables))
        for arg in graphql_field.arguments
    ]
    subfields = to_dict(_read_selection_set(
        graphql_field.selection_set,
        graph_type=field.type,
        fragments=fragments,
        variables=variables,
    ))
    field_query = field(*args, **subfields)
    return (key, field_query)


def _get_field(graph_type, field_name):
    while not isinstance(graph_type, schema.ObjectType):
        graph_type = graph_type.element_type

    return getattr(graph_type.fields, field_name)


def _read_value(value, variables):
    if isinstance(value, graphql_ast.BooleanValue):
        return value.value
    elif isinstance(value, graphql_ast.FloatValue):
        return float(value.value)
    elif isinstance(value, graphql_ast.IntValue):
        return int(value.value)
    elif isinstance(value, graphql_ast.ListValue):
        return [
            _read_value(element, variables=variables)
            for element in value.values
        ]
    elif isinstance(value, graphql_ast.ObjectValue):
        return Object(to_dict(
            (field.name.value, _read_value(field.value, variables=variables))
            for field in value.fields
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
