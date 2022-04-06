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
  _ = plt.hist(sorted_vals, bins=50, range=(0.85, 1.15))
  mean = np.asarray(sorted_vals).mean()
  max = np.asarray(sorted_vals).max()
  plt.axvline(mean, color='k', linestyle='dashed', linewidth=1)
  plt.title(f"Score {market} for {bookie_list}:\n Mean = {mean:.3f}; Max = {max:.3f}")
  plt.show()


def findBets(unified_dicts, market):  
  # only iterate those dicts for which we have the respective data
  eligible_dicts = {}
  for bookie, unified_dict in unified_dicts.items(): 
    if market in list(unified_dict[ list(unified_dict.keys())[0] ].columns):
      eligible_dicts[bookie] = unified_dict
  print(f"The following bookies have data for {market}: {eligible_dicts.keys()}")

  # find best odds
  best_odds_data = {}
  for bookie, unified_dict in eligible_dicts.items():  
    for league, df in unified_dict.items():
      for index,row in df.iterrows():
        if not index or not row[market]:
          continue
        date, home_team, away_team = index
        odds = [float(x) for x in row[market].split('\n')]
        if not index in best_odds_data.keys():
          #print(f"Found new game: {date}: {home_team} vs {away_team} -> Odds: {joinEm(odds)}. Score: { score(odds) }")
          best_odds_data[index] = [odds, [bookie]*len(odds)]
        else:
          #print(f"Game already exists: {date}: {home_team} vs {away_team}")      
          old_odds = best_odds_data[index][0]
          old_bookies = best_odds_data[index][1]
          old_score = score(old_odds)
          improved = False
          for i in range(len(odds)):
            if best_odds_data[index][0][i] < odds[i]:
              best_odds_data[index][0][i] = odds[i]
              best_odds_data[index][1][i] = bookie
              improved = True
          # if improved:
          #   new_odds = best_odds_data[index][0]
          #   new_score = score(new_odds)
          #   print(f"  Improved Odds: {old_odds} --> {new_odds}. Improved score: {old_score} --> {new_score}")

  # verify best odds
  surebets = {}
  best_scores = {}
  for index, odds_data in best_odds_data.items():
    date, home_team, away_team = index
    odds = odds_data[0]
    bookies = odds_data[1]
    curr_score = float(score(odds))
    best_scores[index] = curr_score
    #print(f"Best score {home_team} vs. {away_team}: {curr_score} -> {joinEm(bookies)")
    if curr_score > 1.0:
      print(f"Surebet: {date.date()}: {home_team} vs {away_team} " + \
            f"-> Odds: {joinEm(odds)} " + \
            f"-> Bookies: {joinEm(bookies)} (score: {curr_score})")
      surebets[index] = odds_data

  # print stats
  print(f"Done. Found {len(surebets)} surebets for {market}.")
  printHistogram(best_scores, bookies, market)


###########################################################################################################
#  MAIN

# load unified results
unified_dicts = {}
for bookie in bookies:
  unified_dict = pickle.load(open(f'./scraped/dict_{bookie}_unified.pck', 'rb'))  
  print(f"{bookie}: Length: {len(unified_dict)}. Keys: {unified_dict.keys()}")
  unified_dicts[bookie] = unified_dict

findBets(unified_dicts, '3-way')
findBets(unified_dicts, 'btts')

