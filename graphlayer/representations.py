object_representation = object()


class ObjectResult(object):
    def __init__(self, values):
        for key in values:
            setattr(self, key, values[key])
