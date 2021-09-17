"""
    This module implements the Abduction Module while using the
Predicate approach to filter computation. As such, it is closer to
the approach explained in the paper.
"""
from abc import ABC, abstractmethod
from progress.bar import Bar
import time
import datetime as dt

from IPython.display import display
from ipywidgets import interactive

import mpld3
from mpld3._server import serve
from abduction_memorability.event import Event
from abduction_memorability.memory import Memory
from abduction_memorability.predicate import Predicate
from abduction_memorability.predicate_filter import Filter, OptimizedFilter
from abduction_memorability.helpers import Helpers
import math as m
from matplotlib import pyplot as plt


class AbductionModule(ABC):
    """
        The Abduction Module class serves as the main class of this project.
    It models a modules which takes as input a memory, (= a set of events),
    and is able to compute for each of its members a complexity score, a
    "memorability" score, and other derivatives.

    To initialize, the module can take a memory object, in which case this
    memory is used to compute all scores (this might take a few minutes,
    depending on the size/settings).
    Different options are available in the __init__ method, see the doc
    for it.
    """

    def __init__(self, memory: Memory = None):
        self._memory: Memory = memory
        print(f"Loaded the memory with {len(self._memory)} items!")

    @abstractmethod
    def abduction(self, consequence: Event):
        """
            The abduction method takes a consequence event as input and
        returns the most notable events, w.r.t. to this event.
        """
        pass


class SurpriseAbductionModule(AbductionModule):
    def __init__(self, memory=None, **kwargs):
        super().__init__(memory)
        self._predicates: list[Predicate] = kwargs.get("predicates", [])
        self.max_depth = kwargs.get("max_depth", 4)
        self.max_complex = kwargs.get("max_complexity", 40)
        # Field to keep all figures in memory before plotting them
        self.__figures = []
        # Init the complexities fields
        self.__complexities = {}
        self.__designations = {}
        self.__recipes = {}
        self.__surprises = {}
        self.__memories_by_event = {}
        self.__predicates_by_event = {}
        self.should_refresh = False
        if self._memory is not None:
            self.__compute_complexities()
            self.__computes_all_abs_surprises()

    def abduction(self, consequence_id: int):
        """Implementation of the super method "abduction"
        Args:
            consequence_id (int): ID of the event from the memory
        Returns:
            TYPE: Description
        """
        return self.__surprise_scores(self._memory.get_event_by_id(consequence_id))

    #############################################################
    #       ACCESSORS                                           #
    #############################################################

    def get_event_complexity(self, event_id: int) -> float:
        """Returns the complexity of the event corresponding
        to the given id
        Args:
            event_id (int): unique integer iD of the event
        Returns:
            float: the complexity score of the event
        """
        try:
            return self.__complexities[self._memory.get_event_by_id(event_id)]
        except IndexError:
            print(f'Complexity not found for {event_id}')
            return -1

    def get_event_recipe(self, event_id: int):
        """Returns the recipe (list of filters) used to retrieve the
        given event with id
        Args:
            event_id (int): the integer iD of the event
        Returns:
            list[str]: list of string predicates to retrieve the event.
        """
        try:
            return self.__recipes[self._memory.get_event_by_id(event_id)]
        except IndexError:
            print(f'Recipe not found for {event_id}')
            return -1

    def __compute_complexities(self):
        """
            Helper method called to comput the complexity score for every event
        in the memory.
        """
        # Initializing the different arrays
        for event in self._memory:
            self.__complexities[event] = m.inf
            self.__predicates_by_event[event] = set()
            self.__memories_by_event[event] = []
            self.__recipes[event] = [[], []]
        # Calling the computation method
        self.__complexity_iterative()

    def get_surprise(self, event_id):
        """
            Get the surprise score of the event corresponding to the
        chosen event_id
        """
        try:
            event = self._memory.get_event_by_id(event_id)
        except Exception:
            return None
        return self.__event_surprise(event)

    def __surprise_relative_id(self, hypothesis_id, consequence_id) -> float:
        """
            Computes the memorability of the event `hypothesis_id` relative
        to the event `consequence_id`, by pasisng the consequence_id as an
        input program for free to all predicates used in the computation.
        Args:
            hypothesis_id (TYPE): Description
            consequence_id (TYPE): Description
        Returns:
            float: surprise score for hypothesis, relative to consequence
        """
        try:
            hypothesis = self._memory.get_event_by_id(hypothesis_id)
            consequence = self._memory.get_event_by_id(consequence_id)
        except Exception:
            print("Problem retrieving event in __surprise_relative_id")
        return self.__event_surprise_relative(hypothesis, consequence)

    #############################################################
    #       Helpers                                             #
    #############################################################

    def __surprise_scores(self, consequence: Event):
        """
            Computes the surprise scores relative to the consequence event
        """
        surprises = {}
        associated_memories = self.__memories_by_event[consequence]
        print("Number of associated memories:" + str(len(associated_memories)))
        for recipe in self.__designations[consequence]:
            print(recipe)
        for mem in associated_memories:
            mem: Memory
            mean_cplx = sum([self.__complexities[event] for event in mem])
            mean_cplx = mean_cplx / len(mem)
            for event in mem:
                if event.timestamp < consequence.timestamp:
                    surprise = abs(mean_cplx - self.__complexities[event])
                    if event in surprises:
                        surprises[event].append(surprise)
                    else:
                        surprises[event] = [surprise]
        for event in surprises:
            surprises[event] = sum(surprises[event]) / len(surprises[event])
        best_candidates = sorted(
            surprises.keys(), key=lambda k: surprises[k], reverse=True)[:10]
        for candidate in best_candidates:
            print(f"\t\t{candidate.get_id()}: {surprises[candidate]}")
        return best_candidates

    def __event_surprise_relative(self,
                                  event: Event,
                                  event_consequence: Event):
        """
            Computes the surprise only on predicates that are true
        for the event_consequence
        """
        predicates = self.__predicates_by_event[event]
        scores = []
        events_by_predicates = {}
        for pred in predicates:
            if pred(event_consequence):
                mean_complexity = 0
                num_predicates = 0
                for event_prime in self._memory:
                    if pred(event_prime):
                        mean_complexity += self.__complexities[event_prime]
                        num_predicates += 1
                mean_complexity = mean_complexity / num_predicates
                surprise = abs(mean_complexity - self.__complexities[event])
                scores.append(surprise)
        return sum(scores)/len(scores)

    def __event_surprise(self, event: Event, silent=True):
        """
            Compute the "absolute surprise" of the event passed as argument
        if silend mode is on, nothing will be printed.

        This method computes the surprise by selecting "similar" events (i.e.
        events that appeared in shared submemories when computing complexities)
        and averaging their complexity, and diff-ing it with the actual
        description complexity of the event.

        See the paper for more details.
        """
        mean_complexities = [
            sum(self.__complexities.values())/len(self._memory)]
        if not silent:
            print(f'Mean complexity for all event is {mean_complexities[0]}')
        seen_recipes = set()
        for mem in self.__memories_by_event[event]:
            mem: Memory
            recipe_set = frozenset(mem.recipe())
            if recipe_set in seen_recipes:
                continue
            seen_recipes.add(recipe_set)
            cplx = []
            for e_prime in mem:
                if e_prime != event:
                    cplx.append(self.__complexities[e_prime])
            if len(cplx) > 0:
                mean_complexities.append(sum(cplx)/len(cplx))
                if not silent:
                    print(f"cplx for {mem.recipe()}(len {len(mem)})" +
                          f" is {sum(cplx)/len(cplx)}")
        return abs(
            self.__complexities[event] - sum(mean_complexities) /
            len(mean_complexities)
        )

    def detect_unusual(self, threshold=4):
        """
            Detect the unusual events as the events for which surprise is over
            a given threshold
        """
        to_ret = {}
        for event in self.__surprises:
            if self.__surprises[event] >= threshold:
                to_ret[event] = self.__surprises[event]
        return to_ret

    #############################################################
    #   COMPUTING LOOPS                                         #
    #############################################################

    def __computes_all_abs_surprises(self, should_plot=True):
        """
            Computes and plots the surprises for all events in the memory
        """
        surprises = {}
        print("Computing surprise scores for all events !")
        with Bar(max=len(self._memory)) as bar:
            for event in self._memory:
                surprises[event] = self.__event_surprise(event)
                bar.next()
        if should_plot:
            fig = self.plot(
                alternative=surprises,
                title="Memorability Scores"
            )
            self.__figures.append(fig)
        self.__surprises = surprises

    def __one_complexity_iteration(self, pass_number: int,
                                   current_memories: list) -> list:
        """One iteration for the computation of the complexities of all events in
        the memory.

        This method goes through all  the memories passed in the argument list,
        then computes for each one all possible filters. When an event is singled out,
        the length of the retrieval path is set to be the complexity of this event.
        A list is returned, containing the memorires to be explored for the next iteration
        
        Args:
            pass_number (int): depth of the current pass
            current_memories (list): all the memories to be explored
        
        Returns:
            list: A list of (memory, complexity) to be explored at the next 
        iteration
        """
        # if the max depth is reached, return nothing to explore for the next
        # round, this will effectively stop the computation
        if pass_number >= self.max_depth:
            return []
        print(f'Starting pass {pass_number} of length {len(current_memories)} ')
        start_time = time.time()
        improved = 0
        next_memories = []
        with Bar(f'pass {pass_number}', max=len(current_memories)) as progress_bar:
            for pair_index in range(len(current_memories)):
                pair = current_memories[pair_index]
                mem = pair[0]
                prev_complex = pair[1]
                # print(" -> ", len(mem), prev_complex)
                progress_bar.next()
                num_predicates = len(self._predicates)
                if len(mem) != 0 and prev_complex < self.max_complex:
                    for index in range(len(self._predicates)):
                        program = 0
                        while program > -1:
                            predicate = self._predicates[index](mem, program)
                            filt = OptimizedFilter(predicate)
                            new_mem = filt(mem)
                            if new_mem is None:
                                break
                            if len(new_mem) == len(mem):
                                program += 1
                                continue
                            for event in new_mem:
                                self.__predicates_by_event[event].add(predicate)
                                self.__memories_by_event[event].append(new_mem)
                            if len(new_mem) == 1:
                                event = new_mem.item()
                                new_complex = predicate.program_length() +\
                                    m.log2(num_predicates) + 1 + prev_complex
                                if event in self.__designations:
                                    self.__designations[event].append(
                                        (new_mem.recipe(), new_complex))
                                else:
                                    self.__designations[event] = [
                                        (new_mem.recipe(), new_complex)]
                                new_complex = predicate.program_length() +\
                                    m.log2(num_predicates) + 1 + prev_complex
                                if self.__complexities[event] > new_complex:
                                    improved += 1
                                    self.__complexities[event] = new_complex
                                    self.__recipes[event] = new_mem.recipe()
                            if len(new_mem) > 1:
                                new_complex = predicate.program_length() +\
                                    m.log2(num_predicates) + 1 + prev_complex
                                next_memories.append((new_mem, new_complex))
                            program += 1
        end_time = time.time()
        print(f"Finished pass {pass_number} in {end_time - start_time}s.")
        print(f"Improved complexity for {improved} event(s)")
        return next_memories

    def __complexity_iterative(self, should_plot=True):
        """
            Computes the complexities for all events in the memory of this
        module.
        Args:
            should_plot (bool, optional): Whether plots are made or not (yes!)
        """

        current_memories = [(self._memory, 0)]
        next_memories = []
        pass_number = 0
        figures = []
        print(f"Computing complexities with {self.max_depth} passes")
        # Looping trhough passes
        while len(current_memories) > 0:
            next_memories = self.__one_complexity_iteration(
                pass_number,
                current_memories)
            pass_number += 1
            current_memories = next_memories
            # Commented for notebook
            pass_figure = self.plot(title=f"After {pass_number} pass(es)")
            self.__figures.append(pass_figure)

    #############################################################
    #           PLOTTING AND PRINTING STUFF                     #
    #############################################################

    def plot(self, **kwargs):
        """
            Plot the events and their complexity
        This method is based on the mpld3 library, which allows to write the mpl
        into an HTML file to be served to a local port and displayed in a web
        browser.

        Options:
            title (str): the title of the figure
            alternative (dict(event->float)): NONE
            datetime (boolean): whether printing datetime for timestamps, or
        using raw integer representation (default=True)
        Returns:
            the HTML object used in mpld3 to display the graph
        """
        alternative = kwargs.get("alternative", None)
        dt_timestamp = kwargs.get("datetime", True)
        x_axis = []
        y_axis = []
        labels = []
        index = 0
        c = []
        possible_colors = ["b", 'g', 'r', 'c', 'm', 'y', 'k']
        max_color = 0
        colors_labels = {}
        data = self.__complexities
        if alternative is not None:
            data = alternative
        for event in data:
            if data[event] < m.inf:
                index += 1
                if dt_timestamp:
                    x_axis.append(dt.datetime.fromtimestamp(event.timestamp))
                else:
                    x_axis.append(event.timestamp)
                y_axis.append(data[event])
                label = str(event.get_id()) + ": " + str(event.label) + "\n"
                e_label = event.label
                if e_label in colors_labels:
                    c.append(colors_labels[e_label])
                else:
                    c.append(possible_colors[max_color])
                    colors_labels[e_label] = possible_colors[max_color]
                    max_color += 1
                    max_color = max_color % len(possible_colors)
                for recipe in self.__recipes[event]:
                    label = label + "|" + recipe
                labels.append(label)
        norm = plt.Normalize(1, 4)

        fig, ax = plt.subplots()
        fig.set_size_inches(17, 10)
        ax.set_title(kwargs.get("title", ""), fontsize=30)
        scatter = plt.scatter(x_axis, y_axis, c=c,
                              s=100, norm=norm)
        tooltip = mpld3.plugins.PointLabelTooltip(scatter,
                                                  labels=labels)
        ax.set_xlabel("Time (epoch)", fontsize=30)
        ax.set_ylabel("Complexity", fontsize=30)
        mpld3.plugins.connect(fig, tooltip)
        try:
            __IPYTHON__
            display(fig)
        except Exception:
            print("Not running from IPython, displaying everything at the end!")
        return mpld3.fig_to_html(fig)

    def print_memory(self):
        """
            Prints all the events in the memory
        """
        self._memory.print_all_events()

    def print_info(self, e_id):
        """
            Prints different info about the event
        """
        event = self._memory.get_event_by_id(e_id)
        memories = self.__memories_by_event[event]
        print(f'{event} is in memory, with {len(memories)} associated memories')
        print(f'Its complexity is {self.__complexities[event]}')
        print(f'now computing surprise with verbosity')
        self.__event_surprise(event, silent=False)

    def plot_roc(self, gt=None):
        """
            Function to plot the ROC curve based on the ground truth given by
        the "gt" arg
        """
        filtered = {}
        tp_rates = []
        fp_rates = []
        max_lim = int(m.ceil(max(self.__surprises.values()))) * 10
        for thresh in range(max_lim, 0, -1):
            _t = thresh / 10
            filtered[thresh] = self.detect_unusual(threshold=_t)
            tp_rate = 0
            fp_rate = 0
            if len(gt) > 0:
                tp_rate = len(
                    set(filtered[thresh].keys()).intersection(gt))/len(gt)
                fp_rate = len(set(filtered[thresh].keys()) -
                              set(filtered[thresh].keys()).intersection(gt)
                              )\
                    / (len(self._memory) - len(gt))
                if len(tp_rates) == 0:
                    tp_rates.append(tp_rate)
                    fp_rates.append(fp_rate)
                elif tp_rate != tp_rates[-1] or fp_rate != fp_rates[-1]:
                    tp_rates.append(tp_rate)
                    fp_rates.append(fp_rate)
            print(
                f'{thresh} : {len(filtered[thresh])}, {tp_rate=}, {fp_rate=}')
        # Closing all previously open figures (that's better for the show)
        for fig_num in plt.get_fignums():
            plt.close(fig_num)
        plt.figure()
        plt.plot(fp_rates, tp_rates)
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curve")
        plt.show()

    #############################################################
    #       MAIN LOOP                                           #
    #############################################################

    def main_loop(self):
        """
            Main loop execution to allow interactive run through the console

            Different commands are available:
                h (help): prints this message
                x (exit)
                i (info mode): displays info about a selected event
                p (plot): display all plots into mpld3 server
                r (reset)
                s (set) : used to tell which events are the true ones
                f (filtering): use the memorability score as an event filtering
                    tool
                a (abduction): use memorability-based abduction to find possible
                    causes for the given event
        """
        true_events = set()
        while True:
            u_in = input(">>> Enter an input (h for help)\n")
            if u_in == "h":
                print()
                print(self.main_loop.__doc__)
            if u_in == "x":
                break
            parsed = u_in.split(" ")
            if parsed[0] == "i":
                print("Info mode!")
                self.print_memory()
                print()
                print("Enter the id of an event to get more info! (x to exit)")
                while True:
                    event_id = input(">>> ")
                    try:
                        event_id = int(event_id)
                        self.print_info(event_id)
                    except Exception:
                        if event_id == "x":
                            break
                        else:
                            print("Enter a valid value: an event id or 'x' to \
                                exit")
            if parsed[0] == "a":
                print('Abduction Mode!')
                print("Enter the id of a suspicious event to get potential \
                    causes")
                while True:
                    event_id = input(">>> ")
                    try:
                        event_id = int(event_id)
                        self.abduction(event_id)
                    except Exception as exc:
                        if event_id == "x":
                            break
                        else:
                            print(exc)
            if parsed[0] == "t":
                print("test mode!")
            if parsed[0] == "f":
                print("filtering mode!")
                self.plot_roc(gt=true_events)
            if parsed[0] == "r":
                print("Resetting true events!")
                self.true_events = set()
            if parsed[0] == "s":
                # Sets the set of true events
                print("Enter the id's of the events, then enter 'x'")
                while True:
                    try:
                        _id = int(input(">>> "))
                        event = self._memory.get_event_by_id(_id)
                        true_events.add(event)
                        print(f'len of true events: {len(true_events)}')
                    except Exception:
                        break
            if parsed[0] == "p":
                serve("".join(self.__figures))
                self.__figures = []
        print("exiting the loop!")
