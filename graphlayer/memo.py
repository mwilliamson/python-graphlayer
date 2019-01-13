def memoize(func):
    if not callable(func):
        func = lambdaize(func)

    result = []

    def get():
        if len(result) == 0:
            result.append(func())

        return result[0]

    return get


def lambdaize(value):
    return lambda: value
