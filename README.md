# Memorability computation

## FOREWORD
This project is made to accompany the paper "insert name here<!-- TODO -->".
All work is property of the authors of the paper.

## How to use
Install all the required packages using the command `pip install -t requirements.txt` into your python environment.

The script `run.sh` contains the command to run the main script and load the folder into the python path environment variable of the system.
No further operation should be used.

## What does it do?
The main script runs an **Abduction Module**, that is, an object that loads a number of events, stored in a .csv file, and runs analyzes them
as to compute the descritpion complexity and memorability score for each one. Then, a basic CLI offers different possiblities:
 - Explore the events loaded in the abduction module: all events will be displayed with their ID, their complexity and their characteristics.
 - Plot the different graphs stored in the memory of the module. Some operations, such as the loading of the module, or the computation of memorability
scores, trigger the creation of a graph. A command then allows to display all graphs in a browser window, using the mpld3 plugin.
