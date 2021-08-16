"""
    An implementation of the event object
"""
import json
from dataclasses import dataclass, field, asdict
import matplotlib.pyplot as plt
from collections.abc import Iterable
from matplotlib.collections import PolyCollection
import math
import pandas as pd


@dataclass(frozen=True)
class Label:
    """
        Label class allows to give a tree-like structure on labels
    """
    name: str = "event"
    parent: object = None  # Parent should be a label too
    # storing the different axes relevant for this
    axes: dict = field(default_factory=dict)
    # label, and their possible rankings.

    def ancestors(self) -> list:
        """
            Returns a list of the ancestors of this label
        """
        to_ret = [self]
        while to_ret[-1].has_parent():
            to_ret.append(to_ret[-1].parent)
        return to_ret

    def has_parent(self):
        """
            Returns true if the label has a parent label (false for the root
        label)
        """
        return self.parent is not None

    def __eq__(self, other):
        """
            Equality is defined as equality of parents and self name
        """
        if other.__class__ == Label:
            return self.name == other.name and self.parent == other.parent
        return False

    def __str__(self):
        if self.parent is None:
            return self.name
        else:
            return str(self.parent) + "/" + self.name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash(str(self))

    @classmethod
    def from_str(cls, _str):
        try:
            _dict = json.loads(_str)
        except:
            print(f"{_str} can not be parsed as a json")
            return None
        if _dict is None:
            return None
        if len(_dict) == 0:
            return None
        return Label(
            name=_dict["name"],
            axes=_dict["axes"],
            parent=Label.from_str(json.dumps(_dict["parent"]))
        )
        # spl = _str.split("/")
        # currentLab = Label(spl[0])
        # parentLab = Label(spl[0])
        # for i in range(1, len(spl)):
        #     currentLab = Label(spl[i], parentLab)
        #     parentLab = currentLab
        # return currentLab

    def to_dict_str(self):
        return json.dumps(asdict(self))


@dataclass(frozen=True)
class Event:
    """
        A class to represent an event
    """
    timestamp: int
    characteristics: dict = field(default_factory=dict)
    label: Label = field(default_factory=Label)
    # a default of -1 means the event is still going on.
    duration: int = -1
    _id: int = -1           # A unique identifier of the event
    # context: list = field(default_factory=list)

    def is_going(self, current_time: int) -> bool:
        """
            returns whether, at the time of the request, the event is still 
        going on
        """
        return self.duration == -1 or \
            (self.timestamp + self.duration > current_time >= self.timestamp)

    def get_id(self) -> int:
        return self._id

    def time_intersect(self, t_0, t_1) -> bool:
        """
            Returns whether the event intersects the time interval [t_0, t_1]
        """
        return (self.duration == -1 and self.timestamp < t_1) or \
            (t_0 < self.timestamp + self.duration < t_1) or \
            (t_0 < self.timestamp < t_1)

    def to_dict(self) -> dict:
        """
            Converts the event to a dictionary object.
        """
        to_ret = {
            "timestamp": self.timestamp,
            "label": str(self.label),
            "duration": self.duration
        }
        for char in self.characteristics:
            to_ret[char] = self.characteristics[char]
        return to_ret

    def __hash__(self):
        return hash(self.label) + hash(self.duration) + hash(self.timestamp)

    def to_df(self) -> pd.DataFrame:
        """
            Converts the event object to a pandas dataframe
        """
        return pd.DataFrame(self.to_dict(), index=[0])

    def get_char(self, key: str):
        """
            Getter for any characteristics of the event, or None if the key is not
        in the characteristics of these events.
        """
        if key == "timestamp":
            return self.timestamp
        if key == "duration":
            return self.duration
        if key == 'label':
            return self.label
        return self.characteristics.get(key, None)

    @classmethod
    def load_df(cls, dataframe: pd.DataFrame):
        """
            Loads a dataframe into an event object
        """

    def has_label(self, label: Label):
        """
            Returns whether label is within this event's ancestors
        """
        return label in self.label.ancestors()

    def set_id(self, new_id: int):
        """
            Sets the id of the event, if it has not yet been done
        """
        if self._id < 0:
            self._id = new_id


def display_timeline(event_list: Iterable[Event], **kwargs):
    """
        Display a list of events as a timeline.
        The timeline consists of boxes representing the event's start and stop
    dates

    Different options are available:
        TODO add some options maybe ?
    """
    colors = []
    labels = {}
    verts = []
    max_index = 0
    all_colors = ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]
    col_index = 0
    for event in event_list:
        if event.label not in labels.keys():
            labels[event.label] = max_index
            max_index += 1
        v = [(event.timestamp, labels[event.label] - .4),
             (event.timestamp, labels[event.label] + .4),
             (event.timestamp + event.duration, labels[event.label] + .4),
             (event.timestamp + event.duration, labels[event.label] - .4),
             (event.timestamp, labels[event.label] - .4)]
        verts.append(v)
        colors.append(all_colors[col_index])
        col_index = (col_index + 1) % (len(all_colors))
    bars = PolyCollection(verts, facecolors=colors)
    fig, ax = plt.subplots()
    ax.add_collection(bars)
    ax.autoscale()
    ax.set_xlabel("Timestamp (seconds from epoch)")
    ax.set_yticks(list(labels.values()))
    ax.set_yticklabels([lab.name for lab in labels])
    plt.show()
