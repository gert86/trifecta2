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
url = 'https://www.betfair.com/sport/football'
outfile_name = './scraped/dict_betfair_test.pck'
dict_countries = {
               'german football': ['German Bundesliga', 'German Bundesliga 2'],
        #   'italian football': ['Italian Serie A', 'Italian Serie B'],
        #   'spanish football': ['Spanish La Liga', 'Spanish Segunda Division'],
        #   'english football': ['English Premier League', 'English League 1', 'English League 2'],
        #   'french football': ['French Ligue 1', 'French Ligue 2'],
        #   'dutch football': ['Dutch Eredivisie'],
        #   'belgian football': ['Belgian First Division A'],
        #   'portuguese football': ['Portuguese Primeira Liga']
        }                
market_dict = {
         'over2.5':'Over/Under 2.5 Goals', 
         'btts':'Both teams to Score?'
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
for country in dict_countries:
  curr_loop_str = f"{country}"
  try:
    for league_idx in range(0, len(dict_countries[country])):        
      count = count + 1
      league = dict_countries[country][league_idx]
      curr_loop_str = (f"{country}/{league}")
      print(f"League {count} of {num_leagues}: {curr_loop_str}...")

      # click on competitions
      header = driver.find_element(by=By.CLASS_NAME, value='updated-competitions')
      competition = WebDriverWait(header, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@title, "COMPETITIONS")]')))
      competition.click()

      # click on countries button (e.g. "German Football")
      competitions_table = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'mod-multipickazmenu-1057')))
      country_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/div[contains(@data-category,' +'"' + country + '"' + ')]')))
      country_button.click() 

      # click on country's league button (e.g. "German Bundesliga")
      league_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@data-galabel,' +'"' + dict_countries[country][league_idx] + '"' + ')]')))
      league_button.click()
      print(f"  selected league {league}")            

      dict_odds = {}
      for m_key, market in market_dict.items():
        curr_loop_str = (f"{country}/{league}/{market}")
        list_dates = []
        list_teams = []
        list_odds = []

        
        # click on dropdown box and select current market (e.g. "Over/Under 2.5 Goals")
        dropdown = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'marketchooser-container')))
        dropdown.click()
        chooser = WebDriverWait(dropdown, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[contains(text(),'+'"'+str(market)+'"'+')]')))
        chooser.click()
        time.sleep(1)  
        print(f"      selected market {market}")        

        games = WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'event-information')))
        for game in games:
          date_time_str = game.find_element(by=By.XPATH, value='.//*[@class="date ui-countdown"]').text
          list_dates.append(date_time_str)

          odds = game.find_element(by=By.XPATH, value='.//div[contains(@class, "runner-list")]')
          list_odds.append(odds.text)
          
          teams_container = game.find_element(by=By.CLASS_NAME, value='teams-container').text
          list_teams.append(teams_container)
        
        #storing data dicts
        dict_odds[f'dates_{m_key}'] = list_dates        
        dict_odds[f'teams_{m_key}'] = list_teams
        dict_odds[f'odds_{m_key}']  = list_odds
        print(f"      added {len(list_dates)} games")


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
      df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('In-Play', today.strftime("%A, %d %B"), x))
      df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Today', today.strftime("%A, %d %B"), x))
      df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Tomorrow', tomorrow.strftime("%d %b"), x))
      df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(str(today.year) + ' ' + x, '%Y %d %b %H:%M'))

      #storing dataframe of each league in dictionary
      dict_frames[dict_countries[country][league_idx]] = df_data
      print(f"Finished {curr_loop_str}\n\n")
  except Exception as e:
    print(f"\n\nException in {curr_loop_str}: {str(e)}\n\n")
    driver.quit()
    exit(-1)

driver.quit()

for league, df in dict_frames.items():
  print(f"  \n{league}")
  for idx, row in df.iterrows():
    home_team, away_team = str(row['Teams']).split('\n')
    print(f"    {row['Dates']}: {home_team} vs. {away_team}")
    for curr_market in market_dict.keys():
      odds = str(row[curr_market]).replace('\n', ' ')
      print(f"      {curr_market}: {odds}")

#save file
output = open(outfile_name, 'wb')
pickle.dump(dict_frames, output)
output.close()
print(f"Done. Stored to {outfile_name}")

