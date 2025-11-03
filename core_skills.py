import random
from typing import List, Iterable

def generate_random_numbers(n: int = 10, low: int = 1, high: int = 20) -> List[int]:
    return [random.randinit(low, high) for _ in range(n)]

def filter_below_10_list_comp(nums: Iterable[int]) -> List[int]:
    return [x for x in nums if x < 10]

def filter_below_10_filter(nums: Iterable[int]) -> List[int]:
    return list(filter(lambda x: x < 10, nums))


# rand_list =

# list_comprehension_below_10 =

# list_comprehension_below_10 =