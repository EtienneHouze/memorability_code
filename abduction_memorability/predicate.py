"""
    This module defines predicates, as boolean functions operating
over events.

    See the docstring for the class for more information
"""
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod
import datetime as dt

from .memory import Memory
from .event import Event
from .helpers import Helpers

__author__ = "Étienne Houzé"


class Predicate:
    """
        Predicates are defined with a pointer to the memory.#!/usr/bin/env python
    They can then be called on events from this memory. If they are not applicable (
    because the memory is not compatible, index out of bound, etc), calling them will
    return None (undefined) instead of a boolean value. This could be used to optimize
    filtering.
    """

    def __init__(self, mem: Memory, prog: int, aux_predicate=None):
        self._mem = mem
        self._prog = prog
        self.aux_predicate = aux_predicate

    def __call__(self, event: Event) -> bool:
        pass

    def get_mem(self) -> Memory:
        """
            Returns a pointer to the memory considered by the predicate
        """
        return self._mem

    def __eq__(self, other):
        if not isinstance(other, Predicate):
            return False
        else:
            return self.__class__ == other.__class__ and self._prog == other._prog

    def __hash__(self):
        return hash(self._prog) + hash(self.__class__)

    def program_length(self) -> int:
        """
            Computes and returns the number of bits required to describe the program
        """
        return Helpers.bit_length(self._prog)


class DayPredicate(Predicate):

    """
        This predicate tests whether the event happened on a day prog days ago.
    If an auxiliary predicate is given, then the days are counted from the day
    of the auxiliary event.
    """

    def __init__(self, mem: Memory, prog: int, aux_predicate=None):
        super().__init__(mem, prog, aux_predicate=aux_predicate)
        self._days = prog
        self._mem = mem

    def __call__(self, event: Event) -> bool:
        if self._mem.is_comparable():
            return None
        if self.aux_predicate is None:
            e_time = event.get_char("timestamp")
            e_date = dt.datetime.fromtimestamp(e_time)
            last_date = dt.datetime.fromtimestamp(self._mem.get_last_time())
            n_days_ago = last_date - dt.timedelta(days=self._prog)
            return (e_date.year == n_days_ago.year
                    and e_date.month == n_days_ago.month
                    and e_date.day == n_days_ago.day)
        else:
            aux_time = self.aux_predicate.get_char("timestamp")
            aux_date = dt.datetime.fromtimestamp(aux_time)
            e_time = event.get_char("timestamp")
            e_date = dt.datetime.fromtimestamp(e_time)
            n_days_ago = aux_date - dt.timedelta(days=self.prog)
            return (e_date.year == n_days_ago.year and e_date.month == n_days_ago.month
                    and e_date.day == n_days_ago.day)

    def get_day(self):
        return self._days

    def __str__(self):
        return "day(" + str(self._prog) + ")"


class MonthPredicate(Predicate):
    def __init__(self, mem: Memory, prog: int, aux_predicate=None):
        super().__init__(mem, prog, aux_predicate=aux_predicate)
        self._month = prog
        self._mem = mem

    def __call__(self, event: Event) -> bool:
        if self._mem.is_comparable():
            return None
        e_time = event.get_char("timestamp")
        e_date = dt.datetime.fromtimestamp(e_time)
        last_date = dt.datetime.fromtimestamp(self._mem.get_last_time())
        if (last_date.year - e_date.year) * 12 + last_date.month - e_date.month == self._month:
            return True
        return False

    def get_month(self) -> int:
        return self._month

    def __str__(self):
        return "month(" + str(self._prog) + ")"


class AxisRankPredicate(Predicate):
    """
        This kind of predicate needs a pointer to the memory to work, as it has
        to fetch the ranking of the predicate alongside the axis.
    """

    def __init__(self, mem: Memory, prog: int):
        super().__init__(mem, prog)
        self._axis = self._prog // len(self._mem)
        self._rank = self._prog % len(self._mem)
        self._original_axis = self._axis

    def __call__(self, event: Event):
        try:
            axis = self._mem.clever_axes()[self._axis]
            return event in self._mem.get_kth_along_axis(axis[0],
                                                         self._rank,
                                                         revert=axis[1])
        except Exception:
            # to have an error
            return None

    def program_length(self):
        return Helpers.bit_length(self._original_axis) \
            + Helpers.bit_length(self._rank)

    def get_rank(self) -> int:
        return self._rank

    def get_revert(self):
        return self._mem.clever_axes()[self._axis][1]

    def get_axis(self) -> str:
        return self._mem.clever_axes()[self._axis][0]

    def __str__(self):
        return "rank(" + str(self.get_axis()) + ", " + str(self._rank) + ")"

    def __repr__(self):
        return str(self)


class DevicePredicate(Predicate):
    """
        This simple predicate checks the device of the recorded event.
        It returns false for all programs if the event has no attached device.

        Args:
            mem (Memory): pointer to the memory upon which this predicate will
        operate. 
            prog (int): Integer representing which device to use in the
        predicate.
    """

    def __init__(self, mem: Memory, prog: int):
        super().__init__(mem, prog)
        self._device = prog

    def __call__(self, event: Event):
        try:
            return event.get_char("device") == \
                list(self._mem.get_devices())[self._device]
        except Exception as exc:
            return None

    def __str__(self):
        return f"device({list(self._mem.get_devices())[self._device]})"


class LocationPredicate(Predicate):
    """
        This predicate checks the location of the event. If an aux event is 
        specified, then the location checks if they are equal.

        Args:
            mem (Memory): pointer to the memory upon which this predicate will
        operate.
    """

    def __init__(self, mem: Memory, prog: int, aux_predicate=None):
        super().__init__(mem, prog, aux_predicate=aux_predicate)
        self._location = prog

    def __call__(self, event: Event):
        try:
            if self.aux_predicate is not None:
                if self._prog == 0:
                    return event.get_char("Location") == \
                        self.aux_predicate.get_char("Location")
                else:
                    return event.get_char("Location") == \
                        self._mem.get_zones(self._location + 1)
            else:
                return event.get_char("Location") == \
                    self._mem.get_zones(self._location)
        except Exception:
            return None

    def str(self):
        if self.aux_predicate is not None:
            if self._prog == 0:
                return f'location({self.aux_predicate.get_char("Location")})'
            else:
                return f'location({self._mem.get_zones(self._location + 1)})'
        return f"location({self._mem.get_zones(self._location)})"


class HasLabelPredicate(Predicate):
    def __init__(self, mem: Memory, prog: int):
        super().__init__(mem, prog)
        self._label = prog

    def __call__(self, event: Event):
        try:
            return event.has_label(self._mem.labels()[self._label])
        except Exception:
            return None

    def __str__(self):
        return f"label({self._mem.labels()[self._label]})"

    def __repr__(self):
        return str(self)
