from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import pickle
import datetime
import re
import os

# TODO: 
# Some sub-pages like 3-way-halftime, show more than 1 table. 
# Also check the table caption to be the correct table (instead only relying on number of \n in odds)


# PARAMS
url = 'https://www.interwetten.com/en/sport/leaguelist?leagueIds='
data_dir = './data'
outfile_name = os.path.join(f'./{data_dir}', 'dict_interwetten.pck')

dict_leagues = {
               'Germany Bundesliga'     : '1019',
               'Germany 2. Bundesliga'  : '1020',
               'Italy Serie A'          : '1029',
               'Italy Serie B'          : '405298',
               'Spain La Liga'          : '1030',
               'Spain Segunda Division' : '105034',
               'England Premier League' : '1021',
               'England League 1'       : '10467',
               'England League 2'       : '10468',
               'France Ligue 1'         : '1024',
               'France Ligue 2'         : '10617',            
               }   

dict_markets =  {
                '3-way'                 : '&offergroupid=7',
                #'3-way-halftime'        : '&offergroupid=108',
                #'over-under'            : '&offergroupid=8',    # todo: which amount?
                'btts'                  : '&offergroupid=109',
                #'handicap'              : '&offergroupid=10',   # todo: which handicap?
                'double-chance'         : '&offergroupid=55',  # 1X, 12, 2X  -> will be unified after parsing!
                }
              
# checks            
if len(dict_leagues)==0 or len(dict_markets)==0 :
  print(f"Leagues and Markets must both be non-empty!")
  exit(-1)

# chromedriver options and init
options = Options()
#options.headless = True
options.add_argument('window-size=1920x1080')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)
driver.maximize_window()

# click accept cookies
accept = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tru_accept_btn"]')))
accept.click()


#loop through leagues
count = 0
today = datetime.datetime.today()
tomorrow = today + datetime.timedelta(days=1)
dict_frames = {} # 1 dataframe per league to be filled
for league, league_data in dict_leagues.items():
  df_data = pd.DataFrame(columns=['Dates', 'Teams'] + list(dict_markets.keys()))
  df_data = df_data.set_index(['Dates', 'Teams'])  
  count = count + 1
  curr_loop_str = f"{league}"
  print(f"League {count} of {len(dict_leagues)}: {curr_loop_str}...")

  try:  
    for market, market_data in dict_markets.items():
      home_team = away_team = odd_1 = odd_X = odd_2 = text_001 = text_002 = text_003 = ''
         
      # navigate to subpage      
      full_url = url + league_data + market_data
      driver.get(full_url)
      time.sleep(1)

      # get main table children
      children = driver.find_elements(by=By.XPATH, value=f'//*[@id="TBL_Content_{league_data}"]/tbody/tr')

      # children are a mix of dates (class="playtime) and cells containing game data (class="bets)
      # Need to be processed in order
      games_with_dates = []
      date_str = ''
      for child in children:
        if len(child.find_elements(by=By.XPATH,value='.//td[@class="playtime"]')) == 1:
          try:
            date_cell = child.find_element(by=By.XPATH,value='.//td[@class="playtime"]')
            date_time_obj = datetime.datetime.strptime(date_cell.text.strip(), '%d.%m.%Y')
            date_str = date_time_obj.strftime('%Y-%m-%d')            
          except:
            pass
        if len(child.find_elements(by=By.XPATH,value='.//td[@class="bets"]')) == 1:
          game_cell = child.find_element(by=By.XPATH,value='.//td[@class="bets"]')          
          if market in ['3-way', '3-way-halftime'] and game_cell.text.count('\n') == 5:
            home_team, odd_1, _, odd_X, away_team, odd_2 = game_cell.text.split('\n')
          elif market in ['btts'] and game_cell.text.count('\n') == 4:
            teams, text_001, odd_1, text_002, odd_2 = game_cell.text.split('\n')
            if text_001.lower()=='yes' and text_002.lower()=='no' and ' - ' in teams:
              home_team, away_team = [x.strip() for x in teams.split(' - ')]
              odd_X = ''
            else:
              continue
          elif market in ['double-chance'] and game_cell.text.count('\n') == 6:
            teams, text_001, odd_1, text_002, odd_2, text_003, odd_X = game_cell.text.split('\n')
            if text_001.lower()=='1x' and text_002.lower()=='12' and text_003.lower()=='x2' and ' - ' in teams:
              home_team, away_team = [x.strip() for x in teams.split(' - ')]
              # note that we resorted to standard order: [1X, 2X, 12]
            else:
              continue
          else:
            continue


          if date_str != '':
            df_key = (date_str, home_team+'\n'+away_team)
            if not df_key in df_data.index:
              df_data.loc[df_key, :] = None
            df_data.at[df_key, market] = '\n'.join([odd for odd in [odd_1, odd_X, odd_2] if odd != ''])

    # clean data
    df_data = df_data.fillna('')
    #df_data = df_data.replace('SUSPENDED\n', '', regex=True)
    df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # make date being a real datatime object
    df_data = df_data.reset_index()
    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
    df_data = df_data.set_index(['Dates', 'Teams'])

    #storing dataframe of each league in dictionary
    dict_frames[league] = df_data
    print(f"Finished {league} -> Found {len(dict_frames[league])} games\n\n")
  except Exception as e:
    print(f"\n\nException in {curr_loop_str}: {str(e)}\n\n")
    driver.quit()
    exit(-1)

driver.quit()

#save file
output = open(outfile_name, 'wb')
pickle.dump(dict_frames, output)
output.close()
print(f"Done. Stored to {outfile_name}")
