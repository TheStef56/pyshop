import os
import hashlib

def rand_hash256():
    rand_bytes = os.urandom(32)
    hash_ob = hashlib.sha256(rand_bytes)
    return hash_ob.hexdigest()
