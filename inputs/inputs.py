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
import subprocess
from pandas.io import sql
import sqlite3

log = logging.getLogger(__name__)

def join_path(p1,p2):
    return os.path.abspath(os.path.join(p1,p2))

def table_exists(cur,name):
    return len(list(cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='{0}';".format(name))))>0

class SportsFormats(DataFormats):
    events = "events"

def get_team_and_year(r):
    end = r.split("/")[-1]
    team = end[0:3]
    year = end[3:7]
    return team, year

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
            files = [i for i in os.listdir(fold) if os.path.isfile(join_path(fold,i)) if i.endswith(".EVN")]
            years = list(set([i[:4] for i in files]))
            for y in years:
                if not os.path.isfile('{0}/events-{1}.csv'.format(settings.DATA_PATH,y)):
                    cmd = "{cp}cwevent -q -n -f 0-96 -x 0-62 -y {y} {y}*.EV* > {dp}/events-{y}.csv".format(cp = settings.CHADWICK_PATH,  dp = settings.DATA_PATH,y=y)
                    os.chdir(fold)
                    subprocess.call(cmd, shell=True)
                if not os.path.isfile('{0}/games-{1}.csv'.format(settings.DATA_PATH,y)):
                    cmd = "{cp}cwgame -q -n -f 0-83 -y {y} {y}*.EV* > {dp}/games-{y}.csv".format(cp=settings.CHADWICK_PATH,  dp=settings.DATA_PATH,y=y)
                    subprocess.call(cmd, shell=True)
                if not os.path.isfile('{0}/boxes-{1}.csv'.format(settings.DATA_PATH,y)):
                    cmd = "{cp}cwbox -q -X -y {y} {y}*.EV* > {dp}/boxes-{y}.csv".format(cp = settings.CHADWICK_PATH,  dp = settings.DATA_PATH,y=y)
                    os.chdir(fold)
                    subprocess.call(cmd, shell=True)
            efiles +=[join_path(fold,i) for i in os.listdir(fold) if os.path.isfile(join_path(fold,i))]

        con = sqlite3.connect(settings.DB_PATH)
        c = con.cursor()
        if not table_exists(c,"rosters"):
            rfiles = [f for f in efiles if f.endswith(".ROS")]
            rosters = []
            for r in rfiles:
                filestream = open(r)
                team,year = get_team_and_year(r)
                df = pd.read_csv(filestream,names=["id","lastname","firstname","pbat","sbat","team","position"])
                df['year'] = [year for i in xrange(0,df.shape[0])]
                rosters.append(df)
            roster = pd.concat(rosters,axis=0)
            sql.write_frame(roster, name='rosters', con=con)

        game_files = [join_path(settings.DATA_PATH,g) for g in os.listdir(settings.DATA_PATH) if g.startswith('games-')]
        event_files = [join_path(settings.DATA_PATH,e) for e in os.listdir(settings.DATA_PATH) if e.startswith('events-')]

        if not table_exists(c,"games"):
            games = []
            for g in game_files:
                df = pd.read_csv(open(g))
                team,year = get_team_and_year(g)
                df['year'] = [year for i in xrange(0,df.shape[0])]
                df['team'] = [team for i in xrange(0,df.shape[0])]
                games.append(df)
            games = pd.concat(games,axis=0)
            sql.write_frame(games, name='games', con=con)

        if not table_exists(c,"events"):
            events = []
            for e in event_files:
                df = pd.read_csv(open(e))
                team,year = get_team_and_year(e)
                df['year'] = [year for i in xrange(0,df.shape[0])]
                df['team'] = [team for i in xrange(0,df.shape[0])]
                events.append(df)
            events = pd.concat(events,axis=0)
            sql.write_frame(events, name='events', con=con)


        self.data = {
            'rosters' : 'roster',
            'games' : 'games',
            'events' : 'events',
        }