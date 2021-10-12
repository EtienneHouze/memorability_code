"""
    A class to describe the memory structure, without order

the class comes with possible orders, that should be used by predicates.
"""
#pylint:disable=relative-beyond-top-level
import datetime as dt
from abduction_memorability.event import Event, Label, display_timeline
import bisect
from collections.abc import Iterable
import pandas as pd
import numpy as np
import math


class Memory:
    """
        The Memory class contains the structure of a set of events, on which we can
    apply predicates. It is noteworthy that many rankings and axes and labels are stored
    to improve computations, even though they stay out of the theoretical work.

    :Params:
        :events: A basic list of events to initialize the memory
        :recipe: the recipe used to obtain the memory
    """

    def __init__(self, events: Iterable[Event] = None, recipe: list = None, complexity: int = 0):
        self.__events = set()
        # we keep track of the rankings, even though they are not accessible from the
        # outside
        # For each possible axis, we keep a dictionary mapping the value in this axis to
        self.__rankings = {}
        # keeping track of the labels of the events
        self.__labels = {}
        # keeping track of the labels of the
        self.__axes = {}
        # Keeping track of sorted axes: a mapping of axis name to a mapping of values to
        # their order.
        self.__max_event_id = -1
        self.__events_by_day = {}
        self.__events_by_month = {}
        self.__months_sorted = {}
        self.__days_sorted = {}
        self.__events_by_id = {}
        self.__events_by_device = {}
        self.sorted_axes = {}
        self.__events_par_char_value = {}
        self.__recipe = recipe
        self.__last_timestamp = -1
        self.__complexity = complexity
        self.__first_time = math.inf
        if self.__recipe is None:
            self.__recipe = []
        if events is not None:
            self.extend(events)
        else:
            self.extend([])

    def complexity(self) -> int:
        return self.__complexity

    def __len__(self):
        return len(self.__events)

    def item(self) -> Event:
        """
            Returns the item if the memory is a singleton.
        Otherwise, returns None
        """
        if len(self) == 1:
            for event in self.__events:
                return event
        return None

    def get_past_month(self, m_index):
        return self.__months_sorted[m_index]

    def get_past_day(self, d_index):
        return self.__days_sorted[d_index]

    def visualize(self):
        """
            Displays the timeline of events contained in the memory
        """
        display_timeline(self)

    def to_pandas(self) -> pd.DataFrame:
        """
            Returns a pd.DataFrame object representing the collection
        """
        pd_dict = {
            "label": [],
            "timestamp": [],
            "duration": []
            }
        index = 0
        for event in self.__events:
            event:Event
            pd_dict["label"].append(event.label.to_dict_str())
            pd_dict["timestamp"].append(event.timestamp)
            pd_dict["duration"].append(event.duration)
            for key in event.characteristics:
                if key not in pd_dict.keys():
                    pd_dict[key] = [None] * index
                    pd_dict[key].append(event.get_char(key))
                else:
                    pd_dict[key].append(event.get_char(key))
            for key in pd_dict:
                if key not in event.characteristics.keys():
                    if key != "timestamp" and key != "label" and key != "duration":
                        pd_dict[key].append(None)
            index += 1
        return pd.DataFrame.from_dict(pd_dict).replace({None:np.nan})
        # for event in self.__events:
        #     df = df.append(event.to_df(), ignore_index=True)

    def save_to_csv(self, target_file:str) -> None:
        """
            saves the collection into a csv file
        """
        df = self.to_pandas()
        df.to_csv(target_file)

    def __eq__(self, other):
        if not isinstance(other, Memory):
            return False
        return self.__events == other.__events

    @classmethod
    def load_csv(cls, csv_file: str):
        """
            Loads a csv file into a pd dataframe, then an EventCollection
        """
        tmp_df = pd.read_csv(csv_file)
        print(tmp_df.columns)
        events_list = []
        for index, row in tmp_df.iterrows():
            row = row.dropna()
            chars = {}
            for key in row.index:
                if key not in ["Unnamed: 0", "timestamp", "duration", "label"]:
                    chars[key] = row.loc[key]
            print(index)
            new_event = Event(
                timestamp=row.loc["timestamp"],
                duration=row.loc["duration"],
                label=Label.from_str(row.loc["label"]),
                characteristics = chars
                )
            events_list.append(new_event)
        return Memory(events=events_list)

    def recipe(self):
        """
            The recipe stores what operations were required to build the memory
        """
        return self.__recipe

    def get_event_by_id(self, id_entry: int) -> Event:
        """Simple accessor method for an individual event.

        During the creation of the memory, all events are given a unique 
        integer ID. This ID can then be used to retrieve the event from the 
        memory.

        TIP: the ids can be listed by calling the "print_all_events" method.

        Args:
            id_entry (int):  unique id of the event

        Returns:
            Event: the corresponding event
        """
        return self.__events_by_id.get(id_entry, None)

    def get_last_time(self) -> float:
        """
            Get the current last time recorded
        """
        return self.__last_timestamp

    def get_month_events(self, month_str):
        """
            Returns the events from the selected month
        """
        return self.__events_by_month.get(month_str, [])

    def get_day_events(self, day_str):
        """
            Returns the events from the selected day
        """
        return self.__events_by_day.get(day_str, [])

    def first_date(self):
        """
            Returns the datetime object corresponding to the first event
        recorded in the memory
        """
        return dt.datetime.fromtimestamp(self.__first_time)

    def __append(self, event: Event):
        """
            Adds a single element to the memory. All the magic of the 
        memory construction happens here!
        """
        if event.get_id() < 0:
            event = Event(label=event.label,
                          characteristics=event.characteristics,
                          timestamp=event.timestamp,
                          duration=event.duration,
                          _id=self.__max_event_id + 1)
        self.__events.add(event)
        date = dt.datetime.fromtimestamp(event.timestamp)
        day_str = date.strftime("%Y%m%d")
        month_str = date.strftime("%Y%m")
        device = event.get_char("device")
        if device is not None:
            if device not in self.__events_by_device:
                self.__events_by_device[device] = set([event])
            else:
                self.__events_by_device[device].add(event)
        if day_str not in self.__events_by_day:
            self.__events_by_day[day_str] = [event]
        else:
            self.__events_by_day[day_str].append(event)
        if month_str not in self.__events_by_month:
            self.__events_by_month[month_str] = [event]
        else:
            self.__events_by_month[month_str].append(event)
        self.__events_by_id[event.get_id()] = event
        self.__max_event_id = max(event.get_id(), self.__max_event_id)
        self.__last_timestamp = max(event.timestamp, self.__last_timestamp)
        self.__first_time = min(event.timestamp, self.__first_time)
        # Dealing with duration and timestamp
        if "timestamp" not in self.__axes:
            self.__axes["timestamp"] = set([event])
            self.sorted_axes["timestamp"] = []
            self.__events_par_char_value["timestamp"] = {}
        else:
            self.__axes['timestamp'].add(event)
        value = event.timestamp
        bisect.insort(self.sorted_axes['timestamp'], value)
        if value not in self.__events_par_char_value["timestamp"]:
            self.__events_par_char_value["timestamp"][value] = set([event])
        else:
            self.__events_par_char_value["timestamp"][value].add(event)
        if "duration" not in self.__axes:
            self.__axes["duration"] = set([event])
            self.sorted_axes["duration"] = []
            self.__events_par_char_value["duration"] = {}
        else:
            self.__axes['duration'].add(event)
        value = event.duration
        bisect.insort(self.sorted_axes['duration'], value)
        if value not in self.__events_par_char_value["duration"]:
            self.__events_par_char_value["duration"][value] = set([event])
        else:
            self.__events_par_char_value["duration"][value].add(event)
        # Dealing with other axes
        for axis in event.characteristics:
            if axis not in self.__axes:
                self.__axes[axis] = set([event])
                self.sorted_axes[axis] = []
                self.__events_par_char_value[axis] = {}
            else:
                self.__axes[axis].add(event)
            # Using bisect to insert while keeping the order the characteristic of
            # the event
            value = event.get_char(axis)
            bisect.insort(self.sorted_axes[axis], value)
            if value not in self.__events_par_char_value[axis]:
                self.__events_par_char_value[axis][value] = set([event])
            else:
                self.__events_par_char_value[axis][value].add(event)
        for label in event.label.ancestors():
            if label not in self.__labels:
                self.__labels[label] = set([event])
            else:
                self.__labels[label].add(event)

    def get_kth_along_axis(self, axis, k, revert=True) -> set[Event]:
        """
            Returns the list of predicates ranked kth along a given axis
        Returns None if the length of the axis is less than k, which will
        raise a further error and end the search
        """
        if not self.is_comparable():
            return None
        if axis == "Location":
            return set()
        this_axis = self.sorted_axes[axis]
        if k > len(this_axis):
            return []
        if revert:
            return self.__events_par_char_value[axis].get(this_axis[len(this_axis) - 1 - k], None)
        else:
            return self.__events_par_char_value[axis].get(this_axis[k], None)

    def get_events_in_range(self, start:dt.datetime=None, stop:dt.datetime=None):
        """
        TODO
            Returns the events occurring between two dates.
        """
        pass

    def is_comparable(self):
        """
            Check whether we can compare stuff on this memory.
        I.E. checks if the only common label is "event": this means that events are
        too different to apply any comparison operation
        """
        labels = self.labels()
        if len(labels) <= 1:
            return True
        return len(self.__labels[labels[1]]) - len(self.__labels[Label()]) == 0

    def clever_axes(self):
        """
            Returns a list of pairs (axis_name, reverse), on which the events can
        be ranked in this memory. Based on the root label of the memory.
        """
        labels = self.labels()
        root_lab = labels[0]
        if len(labels) == 1:
            return []
        root_lab: Label
        if root_lab == Label():
            root_lab = labels[1]
        if self.is_comparable():
            return [(key, root_lab.axes[key]) for key in root_lab.axes]
        else:
            return []

    def extend(self, events: Iterable[Event]):
        """
            Extends with one or several items. This method should be used for
        every extension operation on the memory, as it calls the private method 
        "__append" which does all the magic.
        """
        for event in events:
            self.__append(event)
        # once everythin is appended, we make sure the axes values are kepts unique
        for axis in list(self.sorted_axes.keys()):
            seen = set()
            seen_add = seen.add
            tmp = [x for x in self.sorted_axes[axis] if not (x in seen or seen_add(x))]
            self.sorted_axes[axis] = tmp
        self.__months_sorted = sorted(list(self.__events_by_month.keys()), reverse=True)
        self.__days_sorted = sorted(list(self.__events_by_day.keys()), reverse=True)

    def print_all_events(self, filter = None):
        """
            Prints all events and their IDs, one per line.
        It is possible to define a filter (from the filter class)
        """
        if filter is not None:
            try:
                # print(len(filter(self)))
                filter(self).print_all_events()
            except:
                print(f"Filter {filter} is not applicable here !")
        else:
            for index in self.__events_by_id:
                print(str(index) + ": " + str(self.__events_by_id[index]))

    def get_devices(self):
        """
            returns a list of devices in the memory
        """
        return self.__events_by_device.keys()

    def get_biggest_id(self) -> int:
        """
            Returns the biggest id in the memory
        """
        return max(self.__events_by_id.keys())

    def labels(self):
        """
            Returns labels ordered by number of occurrences
        """
        return sorted(list(self.__labels.keys()),
                      key=lambda l: len(self.__labels[l]),
                      reverse=True)

    def label_occurrences(self, label):
        """
            For testing only?
        """
        return len(self.__labels[label])

    def axes(self):
        """
            returns axes ordered by number of occurrences
        """
        return sorted(list(self.__axes.keys()),
                      key=lambda l: len(self.__axes[l]),
                      reverse=True)

    def axis_occurrences(self, axis):
        """
            For testing only?
        """
        return len(self.__axes[axis])

    def __sort(self):
        pass

    def __iter__(self):
        return iter(self.__events)
