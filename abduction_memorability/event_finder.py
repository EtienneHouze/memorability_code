"""
    This module brings methods to analyse and use a record of
iCasa and extract events from it
"""
import math
import datetime as dt
from abc import ABC, abstractmethod
import pandas as pd
from .event import Event, Label

ROOT_LABEL = Label()
TEMPERATURE_LABEL = Label(
    name="temperature",
    parent=ROOT_LABEL
)
DAY_LABEL = Label(
    name="day",
    parent=ROOT_LABEL,
    axes={
        "max_temp": True,
        "min_temp": False
    }
)
HOT_LABEL = Label(
    name="hot",
    parent=TEMPERATURE_LABEL,
    axes={
        "max_temp": True
        }
    )
COLD_LABEL = Label(
    name="cold",
    parent=TEMPERATURE_LABEL,
    axes={
        "min_temp": False
        }
    )
DEVICE_LABEL = Label(
    name="device",
    parent=ROOT_LABEL
)
REMOVED_LABEL = Label(
    name="device_removed",
    parent=ROOT_LABEL
)
MOVE_LABEL = Label(
    name="move",
    parent=ROOT_LABEL
)
NOT_HERE_LABEL = Label(
    name="not_here",
    parent=ROOT_LABEL,
    axes = {
        "duration": True
    }
)

def read_csv(file_name: str) -> pd.DataFrame:
    """
        Basic CSV parser.
    The specified file should use the output format of the redis_IO reader
    module.
    """
    df = pd.read_csv(file_name)
    df["time"] = df["time"].apply(pd.to_datetime).values.astype(float) / 10**9
    df.index = df["time"]
    print('Finished loading the CSV file!')
    return df

#pylint:disable=too-few-public-methods
class EventFinder(ABC):
    """
        Basic canvas for all event-finding methods
    """
    @abstractmethod
    def __call__(self, time_series: pd.DataFrame) -> list[Event]:
        pass

class NotHereFinder(EventFinder):
    """
        Finds periods of time when the user is out of the house
    """
    def __init__(self, threshold=dt.timedelta(days=1)):
        super().__init__()
        self.threshold = threshold.total_seconds()

    def __call__(self, time_series:pd.DataFrame):
        events_list = []
        presence_cols = []
        for col_name in time_series.columns:
            if "sensedPresence" in col_name:
                presence_cols.append(col_name)
        last_presence_time = -1
        was_here = True
        for index, row in time_series[presence_cols].iterrows():
            # If the user was here, check if this is still the case
            if was_here:
                still_here = any(row)
                if still_here:
                    last_presence_time = index
                else:
                    was_here = False
            else:
                now_here = any(row)
                if now_here:
                    absence_duration = index - last_presence_time
                    if absence_duration > self.threshold:
                        new_event = Event(
                            label = NOT_HERE_LABEL,
                            timestamp = index,
                            duration = absence_duration
                        )
                        events_list.append(new_event)
                    was_here = True
                else:
                    pass
        return events_list



class ColdEventFinder(EventFinder):
    """
        Finds all cold periods from the thermometers in the data
    Params:
        threshold: temperature below which we record a cold period
    """
    def __init__(self, threshold=13):
        self.threshold = threshold

    def __call__(self, time_series: pd.DataFrame) -> list[Event]:
        temp_columns = []
        events_list = []
        for col_name in time_series.columns:
            if "etienne.temperature" in col_name:
                temp_columns.append(col_name)
        for col_name in temp_columns:
            dev_name = col_name.split(".")[0]
            below = False
            min_temp = math.inf
            start_time = 0
            for index, row in time_series[col_name].items():
                if below:
                    if index == time_series.index[-1] or row > self.threshold:
                        duration = index - start_time
                        loc_name = time_series.loc[index][dev_name + '.Location']
                        event = Event(
                            timestamp = start_time,
                            label = COLD_LABEL,
                            characteristics = {
                                "min_temp": min_temp,
                                "device": dev_name,
                                "location": loc_name
                            },
                            duration = duration
                        )
                        events_list.append(event)
                        min_temp = math.inf
                        below = False
                    else:
                        min_temp = min(min_temp, row)
                else:
                    if row < self.threshold:
                        start_time = index
                        min_temp = row
                        below = True
                    else:
                        pass
        return events_list

class DayEventFinder(EventFinder):
    def __init__(self):
        pass

    def __call__(self, time_series: pd.DataFrame) -> list[Event]:
        # We expect time_series to have outdoor information
        out_temp_name = "outdoor.myTemperature"
        current_day_buffer = {
            "start": -1,
            "max_temp": -1,
            "min_temp": 2000
        }
        start_time = time_series.index[0]
        current_day = dt.datetime.fromtimestamp(start_time)
        max_temp = -1000
        min_temp = 2000
        to_ret = []
        for index, row in time_series.iterrows():
            date = dt.datetime.fromtimestamp(index)
            # checking if a new day
            if date.date() != current_day.date():
                event = Event(
                    label=DAY_LABEL,
                    duration=86400,
                    timestamp=start_time,
                    characteristics={
                        "max_temp": max_temp,
                        "min_temp": min_temp
                    }
                )
                to_ret.append(event)
                max_temp = row[out_temp_name]
                min_temp = row[out_temp_name]
                start_time = index
                current_day = dt.datetime.fromtimestamp(start_time)
            else:
                max_temp = max(row[out_temp_name], max_temp)
                min_temp = min(row[out_temp_name], min_temp)
        return to_ret

class DeviceRemovedFinder(EventFinder):
    def __init__(self):
        pass

    def __call__(self, time_series: pd.DataFrame) -> list[Event]:
        devices_and_zones = []
        devices = set()
        for col_name in time_series.columns:
            devices_and_zones.append(col_name.split(".")[0])
        for element in devices_and_zones:
            print(element)
        for elem in devices_and_zones:
            if "time" not in elem and \
               "User" not in elem and \
               "room" not in elem and \
               "outdoor" not in elem:
                print(elem)
                devices.add(elem)
        list_events = []
        for device in devices:
            props = []
            for col in time_series.columns:
                if col.split(".")[0] == device:
                    props.append(col)
            reduced_df = time_series[props]
            removed = False
            start_time = -1
            dev_location = ""
            for index, row in reduced_df.iterrows():
                all_na = True
                for _, value in row.iteritems():
                    if not pd.isna(value):
                        all_na = False
                        break
                if not removed:
                    if all_na:
                        removed = True
                        start_time = index
                    else:
                        dev_location = row[device+".Location"]
                if removed:
                    if not all_na or index == time_series.index[-1]:
                        removed = False
                        duration = index - start_time
                        event = Event(
                            label=REMOVED_LABEL,
                            timestamp = start_time,
                            duration = duration,
                            characteristics = {
                                "device": device,
                                "location": dev_location
                            }
                        )
                        list_events.append(event)
        print(devices)
        return list_events


class HotEventFinder(EventFinder):
    """
        Finds all hot periods from the data
    Params:
        threshold: the temperature above which we record a hot period
    """
    def __init__(self, threshold=23):
        self.threshold = threshold

    def __call__(self, time_series: pd.DataFrame) -> list[Event]:
        temp_columns = []
        events_list = []
        for col_name in time_series.columns:
            if "etienne.temperature" in col_name:
                temp_columns.append(col_name)
        for col_name in temp_columns:
            dev_name = col_name.split(".")[0]
            above = False
            max_temp = -1
            start_time = 0
            for index, row in time_series[col_name].items():
                # getting the current location of the device
                if above:
                    if index == time_series.index[-1] or row < self.threshold:
                        duration = index - start_time
                        loc_name = time_series.loc[index][dev_name + ".Location"]
                        event = Event(
                            timestamp = start_time,
                            label = HOT_LABEL,
                            characteristics = {
                                'max_temp': max_temp,
                                'device': dev_name,
                                'location': loc_name
                            },
                            duration = duration
                        )
                        events_list.append(event)
                        max_temp = -1
                        above = False
                    else:
                        max_temp = max(max_temp, row)
                else:
                    if row > self.threshold:
                        start_time = index
                        max_temp = row
                        above = True
                    else:
                        pass
        return events_list


class MoveEventFinder(EventFinder):
    """
        Finds out if a device has been moved.
    """
    def __init__(self, threshold=5):
        self.threshold = threshold


    def __call__(self, time_series: pd.DataFrame) -> list[Event]:
        # Finding columns and devices with position
        print("finding the movements")
        event_list = []
        move_columns_x = []
        move_columns_y = []
        device_names = set()
        for col_name in time_series.columns:
            if "positionX" in col_name:
                print(col_name)
                device_names.add(col_name.split(".")[0])
                move_columns_x.append(col_name)
            if "positionY" in col_name:
                move_columns_y.append(col_name)
        # looping through all the devices with positions
        for device in device_names:
            x_data = time_series[device + ".positionX"].dropna()
            print(x_data)
            y_data = time_series[device + ".positionY"].dropna()
            for row_num, (index, _) in enumerate(x_data.iteritems()):
                # Testing we're not at the end of the TS
                if index == x_data.index[-2]:
                    break
                current_x_pos = x_data.iloc[row_num]
                next_x_pos = x_data.iloc[row_num + 1]
                current_y_pos = y_data.iloc[row_num]
                next_y_pos = y_data.iloc[row_num]
                distance_moved = math.sqrt((
                    next_x_pos - current_x_pos)**2
                    + (next_y_pos - current_y_pos)**2)
                if distance_moved > self.threshold:
                    event = Event(
                       label = MOVE_LABEL,
                       timestamp = index,
                       duration = time_series.index[row_num + 1] - index,
                       characteristics = {
                           "distance": distance_moved,
                           "object": device
                       }
                    )
                    event_list.append(event)
        return event_list
