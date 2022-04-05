import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fuzzywuzzy import process, fuzz
import pickle
import re
import datetime
import sympy
import os

# Parameters
bookies = ['betfair', 'tipico', 'bwin']

###########################################################################################################
# Helper functions

def score(val1, val2, val3):
  val = 1.0/(1.0/val1 + 1.0/val2 + 1.0/val3)
  return f"{val:.4f}"

def printHistogram(scores, bookie_list): 
  sorted_vals = list(scores.values())
  sorted_vals.sort(reverse=True)
  _ = plt.hist(sorted_vals, bins=50, range=(0.85, 1.15))
  mean = np.asarray(sorted_vals).mean()
  max = np.asarray(sorted_vals).max()
  plt.axvline(mean, color='k', linestyle='dashed', linewidth=1)
  plt.title(f"Score histogram for {bookie_list}:\n Mean = {mean:.3f}; Max = {max:.3f}")
  plt.show()


###########################################################################################################
#  MAIN

# load unified results
unified_dicts = {}
for bookie in bookies:
  unified_dict = pickle.load(open(f'./scraped/dict_{bookie}_unified.pck', 'rb'))  
  print(f"{bookie}: Length: {len(unified_dict)}. Keys: {unified_dict.keys()}")
  unified_dicts[bookie] = unified_dict

best_odds = {}
for bookie, unified_dict in unified_dicts.items():  
  for league, df in unified_dict.items():
    for index,row in df.iterrows():
      date, home_team, away_team = index
      odd_1, odd_X, odd_2 = [float(x) for x in row["3-way"].split('\n')]
      if not index in best_odds.keys():
        #print(f"Found new game: {date}: {home_team} vs {away_team} -> Odds: {odd_1} / {odd_X} / {odd_2}. Score: { score(odd_1,odd_X,odd_2) }")
        best_odds[index] = ((odd_1, odd_X, odd_2), (bookie, bookie, bookie))
      else:
        #print(f"Game already exists: {date}: {home_team} vs {away_team}")      
        old_odds = best_odds[index][0]
        old_bookies = best_odds[index][1]
        old_score = score(old_odds[0], old_odds[1], old_odds[2])
        improved = False

        if best_odds[index][0][0] < odd_1:
          best_odds[index] = ((odd_1, best_odds[index][0][1], best_odds[index][0][2]),    (bookie, best_odds[index][1][1], best_odds[index][1][2]))
          improved = True
        if best_odds[index][0][1] < odd_X:
          best_odds[index] = ((best_odds[index][0][0], odd_X, best_odds[index][0][2]),    (best_odds[index][1][0], bookie, best_odds[index][1][2]))
          improved = True
        if best_odds[index][0][2] < odd_2:
          best_odds[index] = ((best_odds[index][0][0], best_odds[index][0][1], odd_2),    (best_odds[index][1][0], best_odds[index][1][1], bookie))
          improved = True

        if improved:
          new_odds = best_odds[index][0]
          new_score = score(new_odds[0], new_odds[1], new_odds[2])
          #print(f"  Improved Odds: {old_odds} --> {new_odds}. Improved score: {old_score} --> {new_score}")

best_scores = {}
for index, odds in best_odds.items():
  date, home_team, away_team = index
  odd_1, odd_X, odd_2 = odds[0]
  bookie_1, bookie_X, bookie_2 = odds[1]
  curr_score = float(score(odd_1, odd_X, odd_2))
  best_scores[index] = curr_score
  print(f"Best score {home_team} vs. {away_team}: {curr_score} -> {bookie_1}/{bookie_X}/{bookie_2}")
  if curr_score > 1.0:
    print(f"Found surebet: {date}: {home_team} vs {away_team} -> Odds: {odd_1} / {odd_X} / {odd_2}. Score: { curr_score }")
  #else:
  #  print(f"NO surebet: {date}: {home_team} vs {away_team} -> Odds: {odd_1} / {odd_X} / {odd_2}. Score: { curr_score }")  


printHistogram(best_scores, bookies)
print("Done")