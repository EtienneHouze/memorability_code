# Memorability computation

## FOREWORD
This project is made to accompany the paper *What should I notice? Using Alogithmic Information Theory to evaluate the memorability of events in smart homes*.
All work is property of the authors of the paper, Étienne Houzé, Jean-Louis Dessalles, Ada Diaconescu and David Menga.

## How to use
Install all the required packages using the command `pip install -t requirements.txt` into your python environment.

Different Jupyter Notebooks can be found in the `examples` folder, which correspond to the examples presented in the paper.

## How does it work?
Code is found in the `abduction_memorability` python module. Datasets of events are found in the `events` folder.

The most important class there is `SurpiseAbductionModule`, which includes the algorithms presented in the paper. Upon instanciation, this class runs the memorability computation on the events provided in the constructor. Then, its results can be exported to pandas DataFrame, which is used in the notebooks to produce the plots.

