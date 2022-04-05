from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import pickle
import datetime
import re

# PARAMS
url = 'https://www.betfair.com/sport/football'
outfile_name = './scraped/dict_betfair.pck'
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
               'France Ligue 2'         : ('french football','French Ligue 2'),
               } 
              
dict_markets =  {
                '3-way'             : 'Match Odds',          # separate column
                #'over-under_1.5'    : 'Over/Under 1.5 Goals',
                #'over-under_2.5'    : 'Over/Under 2.5 Goals', 
                'btts'              : 'Both teams to Score?',
                #'double-chance'     : 'Double Chance',   # TODO: irgendwas geht damit nicht 
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
time.sleep(2)
accept = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')))         
accept.click()

# # click accept cookies with retries
# num_tries = 0
# success = False
# while num_tries < 3 and success == False:
#   try:
#     accept = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')))         
#     accept.click()
#     success = True
#   except:
#     num_tries = num_tries + 1
#     success = False
#     print(f"Accepting cookies failed {num_tries} times")
#     time.sleep(num_tries)


# set website language to English and wait for reload
language_box = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'ssc-hlsw')))
WebDriverWait(language_box, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ssc-hls'))).click()
WebDriverWait(language_box, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ssc-en_GB'))).click()
WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Over/Under 2.5 Goals")]')))


#loop through leagues
count = 0
today = datetime.datetime.today()
tomorrow = today + datetime.timedelta(days=1)
dict_frames = {} # 1 dataframe per league to be filled
for league, league_data in dict_leagues.items():
  count = count + 1
  curr_loop_str = f"{league}"
  print(f"League {count} of {len(dict_leagues)}: {curr_loop_str}...")
  country, league_id = league_data
  try:    
    # click on competitions
    header = driver.find_element(by=By.CLASS_NAME, value='updated-competitions')
    competition = WebDriverWait(header, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@title, "COMPETITIONS")]')))
    competition.click()

    # click on countries button (e.g. "German Football")
    competitions_table = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'mod-multipickazmenu-1057')))
    country_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/div[contains(@data-category,' +'"' + country + '"' + ')]')))
    country_button.click() 

    # click on country's league button (e.g. "German Bundesliga")
    league_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@data-galabel,' +'"' + league_id + '"' + ')]')))
    league_button.click()

    dict_odds = {}
    for market, market_data in dict_markets.items():
      curr_loop_str = (f"{country}/{league}/{market_data}")
      list_dates = []
      list_teams = []
      list_odds = []

      # 3-way has its own column without a drop down box, for others change the dropdown value
      if market != '3-way':        
        dropdown = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'marketchooser-container')))
        dropdown.click()
        chooser = WebDriverWait(dropdown, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[contains(text(),'+'"'+str(market_data)+'"'+')]')))
        chooser.click()
        time.sleep(1)  

      games = WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'event-information')))              
      for game in games:
        try:
          date_time_str = game.find_element(by=By.XPATH, value='.//*[@class="date ui-countdown"]').text
          list_dates.append(date_time_str)
        except:
          continue        

        class_id = 'market-3-runners' if market=='3-way' else 'market-2-runners'
        odds = game.find_element(by=By.XPATH, value=f'.//div[@class="details-market {class_id}"]')
        list_odds.append(odds.text)
        
        teams_container = game.find_element(by=By.CLASS_NAME, value='teams-container').text
        list_teams.append(teams_container)
      
      #storing 1 data dict per market
      dict_odds[f'dates_{market}'] = list_dates        
      dict_odds[f'teams_{market}'] = list_teams
      dict_odds[f'odds_{market}']  = list_odds

    # concat dicts and make 1 dataframe per league (still inside for loop)
    df_list = []
    for market in dict_markets.keys():
      df_list.append(pd.DataFrame({'Dates':dict_odds[f'dates_{market}'], 'Teams':dict_odds[f'teams_{market}'], market:dict_odds[f'odds_{market}']}).set_index(['Teams', 'Dates'])) 
    df_data = pd.concat(df_list, axis=1, sort=True)            
    df_data.reset_index(inplace=True)
    #df_data.rename(columns={'index':'Teams'}, inplace=True)

    # clean data
    df_data = df_data.fillna('')
    df_data = df_data.replace('SUSPENDED\n', '', regex=True)
    df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # replace words "In-Play", "Today" and "Tomorrow" with numeric dates or add date if missing
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('In-Play', today.strftime("%d %b"), x))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Today', today.strftime("%d %b"), x))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Tomorrow', tomorrow.strftime("%d %b"), x))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('^[0-2][0-9]:[0-5][0-9]$', today.strftime("%d %b") + ' ' + x, x))    
    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(str(today.year) + ' ' + x, '%Y %d %b %H:%M'))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(str(x.date()), '%Y-%m-%d'))
    df_data.set_index(['Dates', 'Teams'], inplace=True)

    #storing dataframe of each league in dictionary
    dict_frames[league] = df_data
    print(f"Finished {league}\n\n")
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
