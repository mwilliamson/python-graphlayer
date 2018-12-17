class ObjectResult(object):
    def __init__(self, values):
        self._values = values
        for key in values:
            setattr(self, key, values[key])
    
    def __nonzero__(self):
        return bool(self._values)
    
    def __bool__(self):
        return bool(self._values)
