import hashlib

def string_to_hash(string):
    if isinstance(string, str):
        string = string.encode('utf-8')
    return int(hashlib.md5(string).hexdigest(), 16)

def hash_fields(cls, fields):
    """
    Helper to provide multiple ways of creating the same hash.

    integer_hash == hash(expression) == string_hash(expression.key)

    So we assume integers are the precomputed hash and strings
    are the stable .key value.

    The purpose of exposing this externally is being able to quickly
    create keys to access items in hashmes keyed by Manifest
    """

    h = 17
    for field in fields:
        if isinstance(field, int):
            num = field
        elif isinstance(field, str):
            num = hash(string_to_hash(field))
        else:
            num = hash(field)
        print(num)
        h = h * 31 + num
    return hash(h)

