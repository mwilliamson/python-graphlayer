def find(predicate, iterable):
    for element in iterable:
        if predicate(element):
            return element
    
    raise ValueError("could not find matching element")
    

def to_dict(iterable):
    result = {}
    
    for key, value in iterable:
        if key in result:
            raise KeyError("key is already in dict: {!r}".format(key))
        
        result[key] = value
    
    return result
