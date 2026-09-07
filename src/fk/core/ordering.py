from fk.core.abstract_data_item import AbstractDataItem


def _move_index(lst: list[int], index_from: int, index_to: int) -> list[int]:
    new_list = lst.copy()
    new_list.insert(index_to if index_to <= index_from else index_to - 1, new_list.pop(index_from))
    return new_list


def _get_indexes(source: list[AbstractDataItem], target: list[AbstractDataItem]) -> list[int]:
    target_uids = [w.get_uid() for w in target]
    return [target_uids.index(w.get_uid()) for w in source]


def _count_deviations(indexes: list[int]) -> int:
    res = 0
    p = -1
    for i in indexes:
        if i != p + 1:
            res += 1
        p = i
    return res


def _next_step(deviations_count: int, indexes: list[int]) -> list[tuple[int, int]]:
    # This algorithm can be improved in at least two ways:
    # - Generate fewer strategies: Order deviations by count and traverse the smallest ones first, AKA breadth-first
    #   tree traversal.
    # - Minor performance improvement: Do not count all deviations every time. It's enough to only check what changed.
    p = -1
    i = 0
    for j in indexes:
        if j != p + 1:
            k = j + 1 if j > i else j
            new_indexes = _move_index(indexes, i, k)
            new_deviations_count = _count_deviations(new_indexes)
            if new_deviations_count == 0:
                return [(indexes[i], k)]
            elif new_deviations_count < deviations_count:
                return [(indexes[i], k)] + _next_step(new_deviations_count, new_indexes)
        p = j
        i += 1
    return []   # No deviation


def get_reordering_strategies(source: list[AbstractDataItem], target: list[AbstractDataItem]) -> list[list[str]]:
    indexes: list[int] = _get_indexes(source, target)
    steps = _next_step(_count_deviations(indexes), indexes)
    return [
        [target[step[0]].get_uid(), str(step[1])]
        for step in steps
    ]
