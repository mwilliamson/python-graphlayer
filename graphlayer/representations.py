class ObjectResult(object):
    def __init__(self, values):
        self._bool = bool(values)
        for key in values:
            setattr(self, key, values[key])
    
    def __nonzero__(self):
        return self._bool
    
    def __bool__(self):
        return self._bool
