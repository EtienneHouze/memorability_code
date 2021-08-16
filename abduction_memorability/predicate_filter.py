"""
    This module defines a filter on the memory by calling a predicate on
all events of the memory
"""
import datetime as dt
from dateutil.relativedelta import relativedelta
from .memory import Memory
from .predicate import Predicate, AxisRankPredicate, MonthPredicate, DayPredicate
from .helpers import timing

class Filter:
    def __init__(self, predicate: Predicate):
        self._predicate = predicate

    def __call__(self, memory: Memory) -> Memory:
        """
            Calling a filter on a memory will return another memory,
        or None if the filter is not compatible.
        """
        selected = []
        for event in memory:
           should_keep = self._predicate(event)
           if should_keep is None:
               return None
           if should_keep:
               selected.append(event)
        old_recipe = memory.recipe()
        return Memory(selected, recipe = old_recipe + [str(self._predicate)])


class OptimizedFilter(Filter):
    """
        An optimized version of filtering.
    Not quite as elegant, but much faster !
    """
    def __init__(self, predicate: Predicate):
        super().__init__(predicate)

    def __call__(self, memory: Memory) -> Memory:
        if isinstance(self._predicate, AxisRankPredicate):
            try:
                selected = self._predicate.get_mem().get_kth_along_axis(
                    self._predicate.get_axis(),
                    self._predicate.get_rank(),
                    revert=self._predicate.get_revert()
                    )
                # print(selected)
                old_recipe = memory.recipe()
                return Memory(selected, recipe= old_recipe + [str(self._predicate)])
            except Exception as exc:
                return None
        if isinstance(self._predicate, MonthPredicate):
            if not self._predicate.get_mem().is_comparable():
                return None
            self._predicate: MonthPredicate
            try:
                target_date = memory.get_past_month(self._predicate.get_month())
                old_recipe = memory.recipe()
                return Memory(
                    memory.get_month_events(target_date),
                    recipe = old_recipe +[str(self._predicate)])
            except Exception as exc:
                return None
        if isinstance(self._predicate, DayPredicate):
            if not self._predicate.get_mem().is_comparable():
                return None
            try:
                target_date = memory.get_past_day(self._predicate.get_day())
                old_recipe = memory.recipe()
                return Memory(
                    memory.get_day_events(target_date),
                    recipe=old_recipe + [str(self._predicate)])
            except:
                return None
        return super().__call__(memory)
