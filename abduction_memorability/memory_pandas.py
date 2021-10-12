import pandas as pd
from abduction_memorability.event import Label
from abduction_memorability.predicate import *


class Memory:
    def __init__(self, events: pd.DataFrame):
        self.__events = events
        self.__events["label_str"] = self.__events["label"].apply(lambda x: str(Label.from_str(x)))

    def filter(self, pred_type: type, prog: int, relative_event=-1) -> Memory:
        if pred_type == HasLabelPredicate:
            if relative_event == -1:
                return Memory(self.__events[self.__events["label"] == self.get_labels[prog]])
            else:
                return Memory(self.__events[self.__events["label"] == self.get_event(relative_id)["label"]])
        else:
            return Memory(pd.DataFrame())

    def get_labels(self) -> list[str]:
        tmp = self.__events
        tmp["freq"] = self.__events.groupby('label_str')['label_str'].transform('count')
        tmp.sort_values('freq', inplace=True, ascending=False)
        return tmp["label_str"].unique().tolist()
