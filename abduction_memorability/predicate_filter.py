"""
    This module defines a filter on the memory by calling a predicate on
all events of the memory
"""
import datetime as dt
from dateutil.relativedelta import relativedelta
from .memory import Memory
from .predicate import Predicate, AxisRankPredicate, MonthPredicate, DayPredicate,\
    HasLabelPredicate, LocationPredicate, RandomChoicePredicate
from .helpers import timing
from abduction_memorability.event import Event


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
        return Memory(selected, recipe=old_recipe + [str(self._predicate)])


class NewFilter:
    def __init__(self, pred_type: type):
        if not issubclass(pred_type, Predicate):
            raise Exception
        self._pred_type = pred_type

    def __call__(self, memory: Memory, pred_prog: int, additional_event: Event = None):
        old_recipe = memory.recipe()
        old_complexity = memory.complexity()
        pred = self._pred_type(memory, pred_prog, aux_predicate=additional_event)
        if self._pred_type == HasLabelPredicate:
            if pred_prog > 6:
                return None
            if additional_event is not None:
                selected = set([])
                for event in memory:
                    event: Event
                    if event.label.distance_to(additional_event.label) == pred_prog:
                        selected.add(event)
                return Memory(selected,
                              recipe=old_recipe + [f"label({pred_prog})"],
                              complexity=old_complexity + pred.program_length())
        elif self._pred_type == LocationPredicate:
            if additional_event is not None:
                if pred_prog > 0:
                    return None
                selected = set([])
                for event in memory:
                    if event.get_char('location') is None:
                        continue
                    if event.get_char('location') == additional_event.get_char('location'):
                        selected.add(event)
                return Memory(selected,
                              recipe=old_recipe + [f"location({pred_prog})"],
                              complexity=old_complexity + pred.program_length())
        elif self._pred_type == RandomChoicePredicate:
            if pred_prog < len(memory):
                i = 0
                for event in memory:
                    if i == pred_prog:
                        return Memory([event],
                                      old_recipe + [f'random({len(memory)})'],
                                      complexity=old_complexity + pred.program_length())
                    i += 1
            else:
                return None
        elif self._pred_type == DayPredicate:
            if pred_prog > 31:
                return None
            selected = []
            t_date = dt.datetime.fromtimestamp(additional_event.timestamp)
            for event in memory:
                e_date = dt.datetime.fromtimestamp(event.timestamp)
                delta = t_date - e_date
                if delta.days == pred_prog:
                    selected.append(event)
            return Memory(selected,
                          old_recipe + [str(pred)],
                          complexity=old_complexity + pred.program_length())
        else:
            pred = self._pred_type(memory, pred_prog, additional_event)
            return None


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
                return Memory(selected, recipe=old_recipe + [str(self._predicate)])
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
                    recipe=old_recipe + [str(self._predicate)])
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
