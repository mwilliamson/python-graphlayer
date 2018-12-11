def many(field):
    return field


def single(field):
    def select_value(values):
        if len(values) == 1:
            return values[0]
        else:
            raise ValueError("expected exactly one value")

    return field.map_values(select_value)


def single_or_null(field):
    def select_value(values):
        if len(values) == 0:
            return None
        elif len(values) == 1:
            return values[0]
        else:
            raise ValueError("expected zero or one values")
    
    return field.map_values(select_value)

