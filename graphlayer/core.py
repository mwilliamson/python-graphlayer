from . import iterables


def executor(expanders):
    expanders_by_type = iterables.to_dict(
        (expander.type, expander)
        for expander in expanders
    )
    
    class Graph(object):
        def expand(self, query, target_representation, representations=None):
            if representations is None:
                representations = {}
            
            expander = expanders_by_type[query.type]
            
            required_representations = iterables.to_dict(
                (key, representations[representation])
                for key, representation in expander.representations.items()
            )
            
            return expander(self, query, **required_representations)
    
    return Graph().expand


def expander(type, target_representation, representations=None):
    if representations is None:
        representations = {}
    
    def register_expander(func):
        func.type = type
        func.representations = representations
        return func
    
    return register_expander

