import pandas as pd
import numpy as np
from fuzzywuzzy import process, fuzz
import pickle
import re
import datetime
import sympy
import os

# Parameters
data_dir = './data'
hist_outfile_name = os.path.join(f'./{data_dir}', 'dict_historic.pck')
bookies = ['betfair', 'tipico', 'bwin', 'interwetten']


fixed_translations = {"Atletico" : "Ath Madrid",
                      "Wolverhampton" : "Wolves",
                      "Wolverhampton Wanderers" : "Wolves",
                      "Hellas" : "Verona",
                      "Inter Milan" : "Inter"
                     }


###########################################################################################################
# Helper functions

def getHistoricData(file_name, enforce_download = False):
  if os.path.isfile(file_name):
    print(f"Historic file {file_name} exists...")
    if not enforce_download:
      return pickle.load(open(file_name, 'rb'))

  print(f'Downloading and {"re-creating" if os.path.isfile(file_name) else "creating"} historic file')
  # TODO: Extend
  dict_countries = {
              'Germany Bundesliga'      :'D1', 
              'Germany 2. Bundesliga'   :'D2',
              'Italy Serie A'           :'I1', 
              'Italy Serie B'           :'I2',
              'Spain La Liga'           :'SP1', 
              'Spain Segunda Division'  :'SP2',
              'England Premier League'  :'E0', 
              'England League 1'        :'E2', 
              'England League 2'        :'E3',
              'France Ligue 1'          : 'F1', 
              'France Ligue 2'          :'F2'
             }
  base_url = "https://www.football-data.co.uk/mmz4281"
  dict_historical = {} 
  for league in dict_countries:
    print(f"Downloading historic data for {league}")
    frames = []
    for i in range(22, 24):    # season 22/23 and 23/24 -> always include most recent season!!!
        season = f"{i}{i+1}"
        full_url = f"{base_url}/{season}/{dict_countries[league]}.csv"
        try:
            df = pd.read_csv(full_url)
        except: # Italian Serie B has an inconsistent encoding!
            df = pd.read_csv(full_url, encoding='unicode_escape')
        df = df.assign(season=i)
        frames.append(df)
    df_frames = pd.concat(frames)
    df_frames = df_frames.rename(columns={'Date':'date', 'HomeTeam':'home_team', 'AwayTeam':'away_team',
                        'FTHG': 'home_goals', 'FTAG': 'away_goals'})
    dict_historical[league] = df_frames

  pickle.dump(dict_historical, open(file_name, 'wb'))
  print(f"File was stored to {file_name}")
  return dict_historical


def unifyNames(dict_unified_names, scraped_dicts):
  for bookie, scraped_dict in scraped_dicts.items():

    #initialize storage (we'll use these dictionaries to match names between betfair and historical_data)
    dict_home_name_matching = {}
    dict_away_name_matching = {}
    #fill the dictionary with a list of names of all home and away teams that will play during the week
    for league in scraped_dict:
      scraped_dict[league].sort_index(inplace=True)
      scraped_dict[league].reset_index(inplace=True)
      scraped_dict[league][['home_team', 'away_team']] = scraped_dict[league]['Teams'].str.extract(r'(.+)\n(.+)')
      for key,val in fixed_translations.items():
         scraped_dict[league] = scraped_dict[league].replace(key, val)
      dict_home_name_matching[league] = scraped_dict[league].groupby('home_team', as_index=False).count()[['home_team']]
      dict_away_name_matching[league] = scraped_dict[league].groupby('away_team', as_index=False).count()[['away_team']]        

    for league in dict_unified_names:
      all_teams = dict_unified_names[league]['home_team'].unique().tolist()
      if league not in dict_home_name_matching or len(dict_home_name_matching[league]) == 0:
          continue

      columns = list(scraped_dict[league].columns)
      markets = [ elem for elem in columns if elem not in ['Teams', 'Dates', 'home_team', 'away_team']]
        
      # matching scraped names with unified names from historical data
      match = lambda x:process.extractOne(x, all_teams, scorer=fuzz.token_set_ratio, score_cutoff=10)
      match_no_nan = lambda x:match(x) if match(x) is not None else x

      dict_home_name_matching[league][['teams_matched', 'score']] = dict_home_name_matching[league]['home_team'].apply(match_no_nan).apply(pd.Series)
      dict_away_name_matching[league][['teams_matched', 'score']] = dict_away_name_matching[league]['away_team'].apply(match_no_nan).apply(pd.Series)      

      # check for suspicious name mappings that will probably cause violations
      num_home_uniq_keys = len(dict_home_name_matching[league]['home_team'])
      num_home_uniq_vals = len(dict_home_name_matching[league]['teams_matched'].unique())
      if num_home_uniq_keys != num_home_uniq_vals:
        print(f"\nPossible violation in HOME name mapping of {league} / {bookie}: {num_home_uniq_keys} vs. {num_home_uniq_vals} teams")
      num_away_uniq_keys = len(dict_away_name_matching[league]['away_team'])
      num_away_uniq_vals = len(dict_away_name_matching[league]['teams_matched'].unique()) 
      if num_away_uniq_keys != num_away_uniq_vals:
        print(f"\nPossible violation in AWAY name mapping of {league} / {bookie}: {num_away_uniq_keys} vs. {num_away_uniq_vals} teams")

      # uncomment to verify violations manually -> look for low scores
      # if league=="England Premier League":
      #  print(f"This is the fuzzy name mapping result for {league}:")
      #  print(dict_home_name_matching[league])
      #  print(dict_away_name_matching[league])
      #  print(f"---------------")

      #Replacing "Historical Data" team names (teams_matched) in  betfair dataframes
      home_teams = pd.merge(scraped_dict[league], dict_home_name_matching[league], on='home_team',
                            how='left')[['Dates'] + markets + ['teams_matched']].rename(columns={'teams_matched':'home_team'})
      away_teams = pd.merge(scraped_dict[league], dict_away_name_matching[league], on='away_team',
                          how='left')[['teams_matched']].rename(columns={'teams_matched':'away_team'})
      
      #updating values
      scraped_dict.update({league:pd.concat([home_teams, away_teams], axis=1)})
      scraped_dict[league] = scraped_dict[league].set_index(['Dates', 'home_team', 'away_team'])


###########################################################################################################
#  MAIN

# get historic data for unified names
dict_historical = getHistoricData(hist_outfile_name)

# load scraping results
scraped_dicts = {}
for bookie in bookies:
  scraped_dict = pickle.load(open(f'./{data_dir}/dict_{bookie}.pck', 'rb'))  
  #print(f"{bookie}: Length: {len(scraped_dict)}. Keys: {scraped_dict.keys()}")
  scraped_dicts[bookie] = scraped_dict  

# unify names
unifyNames(dict_historical, scraped_dicts)

# store
for bookie, scraped_dict in scraped_dicts.items():
  outfile_name = f'./{data_dir}/dict_{bookie}_unified.pck'
  pickle.dump(scraped_dict, open(outfile_name, 'wb'))
  print(f"Done. Stored to {outfile_name}")

