class Object(object):
    def __init__(self, values):
        self._values = values
        for key in values:
            setattr(self, key, values[key])

    def __nonzero__(self):
        return bool(self._values)

    def __bool__(self):
        return bool(self._values)

    def __hash__(self):
        return hash(self._values)

    def __eq__(self, other):
        if isinstance(other, Object):
            return self._values == other._values
        else:
            return NotImplemented

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "Object({!r})".format(self._values)
