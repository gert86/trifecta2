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
dict_countries = {
          'german football': ['germany-17/bundesliga-102842', 'germany-17/2nd-bundesliga-102845'],
        #   'italian football': ['italy-20/serie-a-102846', 'italy-20/serie-b-102848'],
        # ...
        }                
market_dict = {
         'over_under':'Over/Under', 
         'btts'      :'Both Teams to Score?',
         '3way'      :'Result 1X2'
         }

# checks
num_leagues = 0
for country in dict_countries:
  num_leagues = num_leagues + len(dict_countries[country])               
if num_leagues==0 or len(market_dict)==0 :
  print(f"Countries and Markets must both be non-empty!")
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
dict_frames = {} # 1 dataframe per league to be filled
for country in dict_countries:
  curr_loop_str = f"{country}"
  try:        
    for league_idx in range(0, len(dict_countries[country])):
      dict_odds = {}  
      count = count + 1
      league = dict_countries[country][league_idx]
      curr_loop_str = (f"{country}/{league}")
      print(f"League {count} of {num_leagues}: {curr_loop_str}...")

      # navigate to subpage
      full_url = url + league
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

      games = table.find_elements(by=By.XPATH,value='.//ms-event')
      for game in games:
        date_time_str = game.find_element(by=By.XPATH, value='.//ms-prematch-timer').text  # 'Tomorrow / 8:30 PM' or ''
        #date_str, start_time_str = [x.strip() for x in date_time_str.split('/')]

        
        teams = game.find_elements(by=By.XPATH,value='.//div[@class="participant-container"]')
        if len(teams) != 2:
          continue
        home_team = teams[0].text
        away_team = teams[1].text 
        print(f"    {date_time_str}: {home_team} vs. {away_team}")

        markets = game.find_elements(by=By.XPATH,value='.//div[@class="grid-group-container"]/ms-option-group')
        for i in range(0, len(markets)):                                        
          child_options = markets[i].find_elements(by=By.XPATH,value='./ms-option')
          num_child_options = len(child_options)
          curr_market = dropdown_markets[i] if i < len(dropdown_markets) else ''
          if num_child_options < 2 or num_child_options > 3 or curr_market not in market_dict.values():
            continue

          if num_child_options == 3:
            odd_home, odd_draw, odd_away = child_options[0].text, child_options[1].text, child_options[2].text
            print(f"      {curr_market}: {odd_home}, {odd_draw}, {odd_away}")
          elif num_child_options == 2:
            odd_home, odd_away = child_options[0].text, child_options[1].text
            print(f"      {curr_market}: {odd_home}, {odd_away}")    
          else:      
            print(f"      Found no odds for {curr_market}") 
      
      continue                     

      # concat markets and make 1 dataframe per league (still inside for loop)
      df_list = []
      for m_key in market_dict.keys():
        df_list.append(pd.DataFrame({'Dates':dict_odds[f'dates_{m_key}'], 'Teams':dict_odds[f'teams_{m_key}'], m_key:dict_odds[f'odds_{m_key}']}).set_index(['Teams', 'Dates'])) 
      df_data = pd.concat(df_list, axis=1, sort=True)            
      df_data.reset_index(inplace=True)
      df_data.rename(columns={'index':'Teams'}, inplace=True)

      # clean data
      df_data = df_data.fillna('')
      df_data = df_data.replace('SUSPENDED\n', '', regex=True)
      df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

      # replace words "In-Play", "Today" and "Tomorrow" with numeric dates
      today = datetime.datetime.today()
      tomorrow = today + datetime.timedelta(days=1)
      df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('In-Play', today.strftime("%A, %d %B"), x))
      df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Today', today.strftime("%A, %d %B"), x))
      df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Tomorrow', tomorrow.strftime("%A, %d %B"), x))
      df_data['Dates'] = df_data['Dates'].apply(lambda x: x.split(',')[1].strip())
      df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(str(today.year) + ' ' + x, '%Y %d %B'))

      #storing dataframe of each league in dictionary
      dict_frames[dict_countries[country][league_idx]] = df_data
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

# WORKS ALMOST
