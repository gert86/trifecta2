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
url = 'https://sports.tipico.de/en/all/football/'
outfile_name = './scraped/dict_tipico.pck'
# Note: Tipico allows a filter for all these leagues in 1 page with a dedicated URL (would be lot faster) 
dict_countries = {
          'german football': ['germany/bundesliga', 'germany/2-bundesliga'],
        #   'italian football': ['italy/serie-a', 'italy/serie-b'],
        #   'spanish football': ['spain/la-liga', 'spain/la-liga-2'],
        #   'english football': ['england/premier-league', 'england/league-one', 'england/league-two'],
        #   'french football': ['france/ligue-1', 'france/ligue-2'],
        #   'dutch football': ['netherlands/eredivisie'],
        #   'belgian football': ['belgium/first-division-a'],
        #   'portuguese football': ['portugal/primeira-liga']
        }                      
market_dict = {
         'over_under':'Over/Under', 
         'btts'      :'Both Teams to Score',
         '3way'      :'3-Way'
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
accept = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="_evidon-accept-button"]')))
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
          
      # TODO: Currently not changing dropdown boxes
      # Use the following code to change dd values (BEFORE getting dropdowns)
      # Current problem: Site does not allow the same selected value in different dds
      #first_dropdown = Select(dropdowns[0])
      #first_dropdown.select_by_visible_text(market)            
      dropdowns = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'SportHeader-styles-drop-down')))
      dropdown_markets = []
      for i in range(0, len(dropdowns)):
        dropdown_markets.append(Select(dropdowns[i]).first_selected_option.accessible_name)
      if not set(market_dict.values()).issubset(set(dropdown_markets)):
        print(f"Not all configured markets {market_dict.values()} are visible: {dropdown_markets}")
        exit(-1)    

          
      # get table and immediate children    
      table = driver.find_element(by=By.XPATH, value='//*[@id="app"]/main/main/section/div/div[1]/div/div/div')            
      children=table.find_elements(by=By.XPATH,value='./*')

      # children are a mix of dates (<div>) and cells containing game data (<a>). 
      # Need to be processed in order
      games_with_dates = []
      curr_date = ''
      for child in children:
        if child.tag_name == 'div':
          try:
            if ',' in child.text:
              date_time_obj = datetime.datetime.strptime(child.text.split(',')[1].strip(), '%d.%m').replace(year=datetime.datetime.now().year)
              curr_date = date_time_obj.strftime('%Y-%m-%d')
          except:
            pass
        if child.tag_name == 'a':
          games_with_dates.append((child, curr_date))
      print(f"  there are {len(games_with_dates)} games ...")

      # that would be the easy way, if we would not need the dates
      #games = table.find_elements(by=By.XPATH,value='./a[@class="EventRow-styles-event-row"]')
      
      for game,date_str in games_with_dates:
        child_divs=game.find_elements(by=By.XPATH,value='./div')
        if len(child_divs) < 3:
          continue
        if len(child_divs[0].find_elements(by=By.XPATH, value='.//*[@class="EventDateTime-styles-time EventDateTime-styles-no-date"]')) != 1:
          continue
        if len(child_divs[1].find_elements(by=By.XPATH,value='.//*[@class="EventTeams-styles-team-title"]')) != 2:
          continue

        start_time_str = child_divs[0].find_element(by=By.XPATH, value='.//*[@class="EventDateTime-styles-time EventDateTime-styles-no-date"]').text
        home_team = child_divs[1].find_elements(by=By.XPATH,value='.//*[@class="EventTeams-styles-team-title"]')[0].text
        away_team = child_divs[1].find_elements(by=By.XPATH,value='.//*[@class="EventTeams-styles-team-title"]')[1].text
        print(f"    {date_str} {start_time_str}: {home_team} vs. {away_team}")

        for i in range(2, len(child_divs)):
          odd_buttons = child_divs[i].find_elements(by=By.XPATH,value='.//button')
          num_odd_buttons = len(odd_buttons)
          curr_market = dropdown_markets[i-2] if i-2 < len(dropdown_markets) else ''
          if num_odd_buttons < 2 or num_odd_buttons > 3 or curr_market not in market_dict.values():
            continue
          
          if num_odd_buttons == 3:
            odd_home, odd_draw, odd_away = odd_buttons[0].text, odd_buttons[1].text, odd_buttons[2].text
            print(f"      {curr_market}: {odd_home}, {odd_draw}, {odd_away}")
          elif num_odd_buttons == 2:
            odd_home, odd_away = odd_buttons[0].text, odd_buttons[1].text
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
