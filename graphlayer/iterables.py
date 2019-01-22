import collections

_undefined = object()


def find(predicate, iterable, default=_undefined):
    for element in iterable:
        if predicate(element):
            return element

    if default is _undefined:
        raise ValueError("could not find matching element")
    else:
        return default


def partition(predicate, iterable):
    true_values = []
    false_values = []

    for element in iterable:
        if predicate(element):
            values = true_values
        else:
            values = false_values
        values.append(element)

    return true_values, false_values


def to_default_multidict(iterable):
    result = collections.defaultdict(list)

    for key, value in iterable:
        result[key].append(value)

    return result


def to_dict(iterable):
    result = {}

    for key, value in iterable:
        if key in result:
            raise KeyError("key is already in dict: {!r}".format(key))

        result[key] = value

    return result


def to_multidict(iterable):
    result = collections.OrderedDict()

    for key, value in iterable:
        if key not in result:
            result[key] = []

        result[key].append(value)

    return result
