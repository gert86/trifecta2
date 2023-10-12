from helpers import TipicoHelper
import os

# PARAMS
url = 'https://sports.tipico.de/en/all/football/'
data_dir = './data'
outfile_name = os.path.join(f'./{data_dir}', 'dict_tipico.pck')
dict_leagues = {
               'Germany Bundesliga'     : 'germany/bundesliga',
               'Germany 2. Bundesliga'  : 'germany/2-bundesliga',
               'Italy Serie A'          : 'italy/serie-a',
               'Italy Serie B'          : 'italy/serie-b',
               'Spain La Liga'          : 'spain/la-liga',
               'Spain Segunda Division' : 'spain/la-liga-2',
               'England Premier League' : 'england/premier-league', 
               'England League 1'       : 'england/league-one',
               'England League 2'       : 'england/league-two',
               'France Ligue 1'         : 'france/ligue-1',
               'France Ligue 2'         : 'france/ligue-2',
               }    
dict_markets =  {
                '3-way'                 : '3-Way',
                #'over-under'            : 'Over/Under',           # todo: which amount?
                #'handicap'              : 'Handicap',             # todo: which amount?
                'double-chance'         : 'Double chance',        # 1X, 12, 2X -> will be unified after parsing!
                'btts'                  : 'Both Teams to Score',
                #'draw-no-bet'           : 'Draw no bet',
                #'over-under-halftime'   : 'Halftime-Over/Under',  # todo: which amount?               
                }         

# Main
hlp = None
for league, league_url_suffix in dict_leagues.items():
  if hlp == None:
    hlp = TipicoHelper(url+league_url_suffix, dict_markets)
    hlp.acceptCookies()
  else:
    hlp.chrome_hlp.openUrl(url+league_url_suffix)

  hlp.findEventsTable(live=False)
  hlp.setDropdowns()
  hlp.fetchAllMarketOdds(league_name=league)
  first_round = False
assert(hlp != None)    
hlp.saveToFile(outfile_name=outfile_name)
