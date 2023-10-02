import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fuzzywuzzy import process, fuzz
import pickle
import re
import datetime
import sympy
import os
from collections import Counter

# Parameters
bookies = ['betfair', 'tipico', 'bwin', 'interwetten']

# Which leagues to consider
all_leagues = [
               'Germany Bundesliga',      # 18/0/0/0
               'Germany 2. Bundesliga',   # 11/7/0/0
               'Italy Serie A',           # 20/0/2/0
               'Italy Serie B',           # 10/0/10/0 (tipico,bwin fanden nur 10 Spiele)
               'Spain La Liga',           # 20/1/4/0
               'Spain Segunda Division',  # 11/0/0/0
               'England Premier League',  # 8/12/0/0
               'England League 1',        # 8/4/0/0
               'England League 2',        # 0/12/0/11
               'France Ligue 1',          # 8/10/0/0 (bwin fand nur 8 Spiele)
               'France Ligue 2',          # 8/1/0/0
               ]  


###########################################################################################################
# Helper functions

def score(vals):
  val = 1.0/((1.0/np.asarray(vals)).sum())
  return f"{val:.4f}"

def joinEm(vals):
  return ' / '.join([str(x) for x in vals]) 

def printHistogram(scores, bookie_list, market):
  if not scores:
    return
  sorted_vals = list(scores.values())
  sorted_vals.sort(reverse=True)  
  mean = np.asarray(sorted_vals).mean()
  maxi = np.asarray(sorted_vals).max()
  mini = np.asarray(sorted_vals).min()
  _ = plt.hist(sorted_vals, bins=50, range=(min(0.85, mini), 1.15))
  plt.axvline(mean, color='k', linestyle='dashed', linewidth=1)
  plt.axvline(1.0, color='r', linestyle='solid', linewidth=2)
  plt.title(f"Score {market} for {bookie_list}:\n Mean = {mean:.3f}; Max = {maxi:.3f}")
  plt.show()

def printViolations(best_odds_data):
  home_index, away_index = {}, {}
  for index,data in best_odds_data.items():
    date, home_team, away_team = index
    _,_,league = data
    # violation type #1
    if home_team == away_team:
      print(f"VIOLATION in {league}: A team cannot play itself: {home_team} vs {away_team} on {date}")
    # violation type #2  
    if (date, home_team) in home_index.keys():
      print(f"VIOLATION in {league}: On {date} home team '{home_team}' plays '{home_index[(date, home_team)]}' so it cannot play '{away_team}' at same time")
    else:
      home_index[(date, home_team)] = away_team
    # violation type #3  
    if (date, away_team) in away_index.keys():
      print(f"VIOLATION in {league}: On {date} away team '{away_team}' plays '{away_index[(date, away_team)]}' so it cannot play '{home_team}' at same time")
    else:
      away_index[(date, away_team)] = home_team      

def findBets(unified_dicts, market):  
  # only iterate those dicts for which we have the respective data
  eligible_dicts = {}
  for bookie, unified_dict in unified_dicts.items(): 
    if market in list(unified_dict[ list(unified_dict.keys())[0] ].columns):
      eligible_dicts[bookie] = unified_dict
  print(f"\n\nThe following bookies have data for {market}: {eligible_dicts.keys()}")
  print(f"------------------------------------------------------------------------\n")

  # find best odds
  best_odds_data = {}
  coverage = {}
  for bookie, unified_dict in eligible_dicts.items():  
    for league, df in unified_dict.items():
      if league not in all_leagues:
        continue
      for index,row in df.iterrows():
        if not index or not row[market]:
          continue
        date, home_team, away_team = index
        odds = [float(x) for x in row[market].split('\n')]
        if not index in best_odds_data.keys():
          #print(f"Found new game: {date}: {home_team} vs {away_team} -> Odds: {joinEm(odds)}. Score: { score(odds) }")
          best_odds_data[index] = [odds, [bookie]*len(odds), league]
          coverage[index] = 1
        else:
          #print(f"Game already exists: {date}: {home_team} vs {away_team}")      
          for i in range(len(odds)):
            if best_odds_data[index][0][i] < odds[i]:
              best_odds_data[index][0][i] = odds[i]
              best_odds_data[index][1][i] = bookie
          coverage[index] += 1

  # check for violations
  printViolations(best_odds_data)

  # verify best odds
  surebets = {}
  best_scores = {}
  for index, odds_data in best_odds_data.items():
    date, home_team, away_team = index
    odds = odds_data[0]
    bookies = odds_data[1]
    league = odds_data[2]
    curr_score = float(score(odds))
    # TODO: This is actually an approximation
    if market == "double-chance":
      curr_score = curr_score * 2
    best_scores[index] = curr_score
    #print(f"Best score {date}: {home_team} vs. {away_team}: {curr_score} -> {joinEm(bookies)} "
    #      f"(coverage ({coverage[index]})")
    #      #f"(coverage ({len(coverage[index].split(','))}): {coverage[index]})")
    if curr_score > 1.0:
      print(f"Surebet: {date.date()}: {home_team} vs {away_team} " + \
            f"-> Odds: {joinEm(odds)} " + \
            f"-> Bookies: {joinEm(bookies)} (score: {curr_score}) " +\
            f"-> League: {league}"  )
      surebets[index] = odds_data

  # print stats
  print(f"Done. Found {len(surebets)} surebets for {market} out of {len(best_odds_data)} games.\n")
  res = Counter(coverage.values())
  coverage_sorted = sorted(res.items(), reverse=True) 
  for coverage,num in coverage_sorted:
    print(f"Covered by {coverage} bookies: {num} games")

  #printHistogram(best_scores, eligible_dicts.keys(), market)


###########################################################################################################
#  MAIN
# load unified results
unified_dicts = {}
for bookie in bookies:
  unified_dicts[bookie] = pickle.load(open(f'./data/dict_{bookie}_unified.pck', 'rb'))  

findBets(unified_dicts, '3-way')
findBets(unified_dicts, 'btts')
findBets(unified_dicts, 'double-chance')

