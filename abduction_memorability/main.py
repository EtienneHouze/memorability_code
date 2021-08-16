"""
    Main entrypoint for the memorability code example, this script lads a 
    list of events from a csv file, then constructs the abduction module to 
    analyze events, compute their memorability and so on. Then, a simple CLI
    loop allows some interactions with the module.

    Warning: loading and computing complexities on events can take some time, up 
    a few minutes for sets containing thousands of examples.

    If numerous import errors persists, try adding the root folder of the 
    "clean_project" into the PYTHONPATH environmnent variable.
"""
import argparse
try:
    from clean_project.abduction_predicate import SurpriseAbductionModule
    from clean_project.memory import Memory
    from clean_project.predicate import *
except ModuleNotFoundError:
    import sys
    sys.path.append("/home/etienne/thesis/abduction_event/paper/")
    from clean_project.abduction_predicate import SurpriseAbductionModule
    from clean_project.memory import Memory
    from clean_project.predicate import *

EPILOG_STR = "This script is meant to accompany the paper \"Memorability\" score"

def main():
    global EPILOG_STR
    parser = argparse.ArgumentParser(description=__doc__, epilog=EPILOG_STR)
    parser.add_argument("file", help="Name of an event file 'csv' to load")
    parser.add_argument("--depth", help="Maximum depth of retriveal paths used"+ 
        " for complexity computation", default=4, type=int)
    # parser.error("Please enter the path to a file containing events as main " +
    #     "argument.")
    args = parser.parse_args()
    file_name = args.file
    max_depth = args.depth
    print(file_name)
    mem = Memory.load_csv(file_name)
    if len(mem) == 0:
        print("No event in the memory. Is the csv file correct?")
        return
    module = SurpriseAbductionModule(memory=mem,
                                     predicates=[
                                        HasLabelPredicate,
                                        AxisRankPredicate,
                                        DayPredicate,
                                        DevicePredicate,
                                        LocationPredicate
                                        ],
                                     max_depth=max_depth
                                    )
    module.main_loop()


if __name__ == "__main__":
    main()
