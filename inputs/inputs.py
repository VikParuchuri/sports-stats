from __future__ import division
import csv
from percept.conf.base import settings
from percept.utils.input import DataFormats
from percept.tests.framework import CSVInputTester
from percept.datahandlers.inputs import BaseInput
from percept.utils.models import get_namespace
import os
from itertools import chain
import logging
import json
import re
import pandas as pd

log = logging.getLogger(__name__)

def join_path(p1,p2):
    return os.path.abspath(os.path.join(p1,p2))

class SportsFormats(DataFormats):
    events = "events"

class GameInput(BaseInput):
    """
    Extends baseinput to read simpsons scripts
    """
    input_format = SportsFormats.events
    help_text = "Read in baseball event data."
    namespace = get_namespace(__module__)

    def read_input(self, directory, has_header=True):
        """
        directory is a path to a directory with multiple csv files
        """

        efolds = [ join_path(directory,f) for f in os.listdir(directory) if os.path.isdir(os.path.join(directory,f))]
        efiles = []
        for fold in efolds:
            efiles+= [join_path(fold,i) for i in os.listdir(fold) if os.path.isfile(join_path(fold,i))]
        rfiles = [f for f in efiles if f.endswith(".ROS")]
        efiles = [f for f in efiles if not f.endswith(".ROS")]
        rosters = []
        for r in rfiles:
            filestream = open(r)
            end = r.split("/")[-1]
            team = end[0:3]
            year = end[3:7]
            df = pd.read_csv(filestream,names=["id","lastname","firstname","pbat","sbat","team","position"])
            df['year'] = [year for i in xrange(0,df.shape[0])]
            rosters.append(df)
        roster = pd.concat(rosters,axis=0)

        seasons = []
        for e in efiles:
            season=[]
            reader = csv.reader(open(e))
            for row in reader:
                season.append(row)
            seasons.append(season)
        self.data = {
            'rosters' : roster,
            'seasons' : seasons
        }