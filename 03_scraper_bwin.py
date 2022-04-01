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

# PARAMS
url = 'https://sports.bwin.com/en/sports/football-4/betting/'
outfile_name = './scraped/dict_bwin.pck'
dict_leagues = {
               'Germany Bundesliga'     : 'germany-17/bundesliga-102842',
               'Germany 2. Bundesliga'  : 'germany-17/2nd-bundesliga-102845',
               'Italy Serie A'          : 'italy-20/serie-a-102846',
               'Italy Serie B'          : 'italy-20/serie-b-102848',
               'Spain La Liga'          : 'spain-28/laliga-102829',
               'Spain Segunda Division' : 'spain-28/laliga-2-102830',
               'England Premier League' : 'england-14/premier-league-102841', 
               'England League 1'       : 'england-14/league-one-101551',
               'England League 2'       : 'england-14/league-two-101550',
               'France Ligue 1'         : 'france-16/ligue-1-102843',
               'France Ligue 2'         : 'france-16/ligue-2-102376',               
               }    

dict_markets =  {
                '3way'    : 'Result 1X2',
                'over2.5' : 'Over/Under', 
                'btts'    : 'Both Teams to Score?'
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
accept = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')))
accept.click()


#loop through leagues
count = 0
today = datetime.datetime.today()
tomorrow = today + datetime.timedelta(days=1)
dict_frames = {} # 1 dataframe per league to be filled
for league, league_data in dict_leagues.items():
  count = count + 1
  curr_loop_str = f"{league}"
  print(f"League {count} of {len(dict_leagues)}: {curr_loop_str}...")
  league_url_suffix = league_data
  try:       
    # navigate to subpage
    full_url = url + league_url_suffix
    driver.get(full_url)
    time.sleep(2)

    # get main table
    table = driver.find_element(by=By.XPATH, value='//*[@id="main-view"]/ms-fixture-list/div/div/div/div/ms-grid')            
        
    # get dropdowns below main table
    # TODO: Currently not changing dropdown boxes because they are <ms-group-selector> and not <select>        
    WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'group-selector')))
    dropdowns = table.find_elements(by=By.XPATH,value='.//ms-grid-header/div/ms-group-selector[@class="group-selector"]')
    dropdown_markets = []
    for i in range(0, len(dropdowns)):
      dropdown_markets.append(dropdowns[i].text)

    df_data = pd.DataFrame(columns=['Dates', 'Teams']+list(dict_markets.keys()))
    games = table.find_elements(by=By.XPATH,value='.//ms-event')
    for game in games:
      try:
        date_time_str = game.find_element(by=By.XPATH, value='.//ms-prematch-timer').text
      except:
        continue
      date_time_str = re.sub('Today\s*/?\s+',    today.strftime("%d/%m/%y "), date_time_str)
      date_time_str = re.sub('Tomorrow\s*/?\s+', tomorrow.strftime("%d/%m/%y "), date_time_str)
      dt_temp = datetime.datetime.strptime(date_time_str, '%d/%m/%y %I:%M %p')
      date_time_str = dt_temp.strftime('%Y-%m-%d %H:%M')
      date_str = dt_temp.strftime('%Y-%m-%d')

      
      teams = game.find_elements(by=By.XPATH,value='.//div[@class="participant-container"]')
      if len(teams) != 2:
        continue
      home_team = teams[0].text
      away_team = teams[1].text 
      print(f"    {date_str}: {home_team} vs. {away_team}")

      odds_dict = {}
      markets = game.find_elements(by=By.XPATH,value='.//div[@class="grid-group-container"]/ms-option-group')      
      for i in range(0, len(markets)):                                        
        child_options = markets[i].find_elements(by=By.XPATH,value='./ms-option')
        num_child_options = len(child_options)
        curr_market_dd = dropdown_markets[i] if i < len(dropdown_markets) else ''
        if num_child_options < 2 or num_child_options > 3 or curr_market_dd not in dict_markets.values():
          continue

        market = list(dict_markets.keys())[list(dict_markets.values()).index(curr_market_dd)] # key from value
        if num_child_options == 3:
          odd_home, odd_draw, odd_away = child_options[0].text, child_options[1].text, child_options[2].text
          print(f"      {market}: {odd_home}, {odd_draw}, {odd_away}")
          odds_dict[market] = f"{odd_home}\n{odd_draw}\n{odd_away}"
        elif num_child_options == 2:
          odd_home, odd_away = child_options[0].text, child_options[1].text
          print(f"      {market}: {odd_home}, {odd_away}")
          odds_dict[market] = f"{odd_home}\n{odd_away}"  
        else:      
          print(f"      Found no odds for {market}")
          continue 
                             
      tmp = {'Dates': date_str, 'Teams': home_team+'\n'+away_team}
      tmp.update(odds_dict)
      df_data = df_data.append(tmp, ignore_index=True)

    # clean data
    df_data = df_data.fillna('')
    df_data = df_data.replace('SUSPENDED\n', '', regex=True)
    df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))

    #storing dataframe of each league in dictionary
    dict_frames[league] = df_data
    print(f"Finished {curr_loop_str}\n\n")
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
