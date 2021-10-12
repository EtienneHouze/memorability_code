import pytest

# from abduction_memorability.memory_pandas import Memory
from abduction_memorability.memory import Memory
import pandas as pd
from abduction_memorability.event import Label

from abduction_memorability.predicate_filter import NewFilter
from abduction_memorability.predicate import HasLabelPredicate, LocationPredicate, DevicePredicate,\
    RandomChoicePredicate, DayPredicate
from abduction_memorability.abduction_module import SurpriseAbductionModule


@pytest.mark.skip
def test_label():
    df = pd.read_csv("events/420_events.csv")
    mem = Memory.load_csv("events/420_events.csv")
    print(mem.get_labels())


@pytest.mark.skip()
def test_basic():
    df = pd.read_csv("events/420_events.csv")
    mem = Memory(df)
    mem2 = mem.filter(HasLabelPredicate, 0)
    print(df)


def test_filters():
    mem = Memory.load_csv("events/420_events.csv")
    e1 = mem.get_event_by_id(230)
    filt_1 = NewFilter(HasLabelPredicate)
    test_1 = filt_1(mem, 0, e1)
    test_2 = filt_1(mem, 1, e1)
    assert all([event.label == e1.label for event in test_1])
    assert all([event.label.distance_to(e1.label)] for event in test_2)
    assert not all([event.label == e1.label for event in mem])
    e_bis = None
    for event in mem:
        if event not in test_1:
            e_bis = event
            break
    assert e_bis.label != e1.label
    e_bis: Event
    filt_2 = NewFilter(HasLabelPredicate)
    test_2 = filt_2(mem, 0, e_bis)
    assert all([event.label == e_bis.label for event in test_2])


def test_location_filter():
    mem = Memory.load_csv("events/420_events.csv")
    e1 = mem.get_event_by_id(193)
    filt_1 = NewFilter(LocationPredicate)
    test_1 = filt_1(mem, 0, e1)
    assert all([event.get_char("location") == e1.get_char('location') for event in test_1])


def test_labels():
    lab0 = Label(name="l0", parent=None)
    lab1 = Label(name="l1", parent=lab0)
    lab2 = Label(name='lab2', parent=lab0)
    lab3 = Label(name='lab3', parent=lab2)
    assert lab0.distance_to(lab0) == 0
    assert lab0.distance_to(lab3) == 2
    assert lab1.distance_to(lab2) == 2
    assert lab3.distance_to(lab1) == 3


def test_abduction(capsys):
    mem = Memory.load_csv('events/420_events.csv')
    module = SurpriseAbductionModule(memory=mem,
                                     predicates=[
                                         HasLabelPredicate,
                                         DevicePredicate,
                                         LocationPredicate,
                                         RandomChoicePredicate,
                                         DayPredicate
                                     ],
                                     max_depth=3)
    output = module.abduction(193)
    for pair in output:
        print(pair[0].get_id(), pair[1])
    out, err = capsys.readouterr()
    open("out.txt", "w").write(out)
    open("err.txt", "w").write(err)


def test_days_filter():
    mem = Memory.load_csv("events/420_events.csv")
    f = NewFilter(DayPredicate)
    e = mem.get_event_by_id(193)
    test1 = f(mem, 0, e)
    assert all([event.timestamp - e.timestamp <= 86400 for event in test1])
    test2 = f(mem, 2, e)
    assert all([2*86400 <= abs(event.timestamp - e.timestamp) <= 3 * 86400 for event in test2])
