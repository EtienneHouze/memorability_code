import time
import math

def timing(f):
    def timed(*args, **kwargs):
        t_before = time.time()
        results = f(*args, **kwargs)
        timnig = time.time() - t_before
        print(f"function {f} took {timnig}")
        return results

    return timed


class Helpers:
    """
        A short class containing helper functions.
    """
    @classmethod
    def bit_length(cls, integer, use_floor=False) -> float:
        """
            Compute the number of bits required to write the input integer
        It assumes it uses the doubled length encoding, for prefix number notation.
        Params:
            use_floor (False): if set to true, floor operations are used to compute
        the complexity and come with the correct amount of bits.
        """
        if integer is None:
            return 0
        if isinstance(integer, list):
            return sum([cls.bit_length(member) for member in integer])
        if integer == 0:
            return 2
        if integer == 1:
            return 2
        if use_floor:
            base_length = math.floor(math.log2(integer)) + 1
            return 2 * (math.floor(math.log2(base_length)) + 1) + base_length
            return base_length
        base_length = math.log2(integer) + 1
        return 2 * (math.log2(base_length) + 1) + base_length
