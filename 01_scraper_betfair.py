from helpers import BetfairHelper
import os

# PARAMS
url = 'https://www.betfair.com/sport/football'
data_dir = './data'
outfile_name = os.path.join(f'./{data_dir}', 'dict_betfair.pck')
dict_leagues = {
               'Germany Bundesliga'     : ('german football','German Bundesliga'),
               'Germany 2. Bundesliga'  : ('german football', 'German Bundesliga 2'),
               'Italy Serie A'          : ('italian football', 'Italian Serie A'),
               'Italy Serie B'          : ('italian football', 'Italian Serie B'),
               'Spain La Liga'          : ('spanish football', 'Spanish La Liga'),
               'Spain Segunda Division' : ('spanish football', 'Spanish Segunda Division'),
               'England Premier League' : ('english football', 'English Premier League'), 
               'England League 1'       : ('english football', 'English League 1'),
               'England League 2'       : ('english football', 'English League 2'),
               'France Ligue 1'         : ('french football', 'French Ligue 1'),
               'France Ligue 2'         : ('french football','French Ligue 2')
               } 
              
dict_markets =  {
                '3-way'             : 'Match Odds',          # separate column, always use as first in list!
                #'over-under_1.5'    : 'Over/Under 1.5 Goals',
                #'over-under_2.5'    : 'Over/Under 2.5 Goals', 
                'btts'              : 'Both teams to Score?',
                'double-chance'     : 'Double Chance',   # 1X, 2X, 12
                }

# Main
hlp = None
for league, league_data in dict_leagues.items():
  if hlp == None:
    hlp = BetfairHelper(url, dict_markets)
    hlp.acceptCookies()
    hlp.setLanguageEnglish()
  
  hlp.navigateToLeague(league_data)
  hlp.acceptCookies()
  hlp.findEventsTableAndFetch(live=False, league_name=league)  # or split find and fetch?
assert(hlp != None)  
hlp.saveToFile(outfile_name=outfile_name)
