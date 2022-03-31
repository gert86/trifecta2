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
dict_leagues = {
               'Germany Bundesliga'     : 'germany/bundesliga',
              # 'Germany 2. Bundesliga'  :'germany/2-bundesliga',
               'Italy Serie A'          : 'italy/serie-a',
              # 'Italy Serie A'          : 'italy/serie-b',
              # 'Spain La Liga'          : 'spain/la-liga',
              # 'Spain Segunda Division' : 'spain/la-liga-2',
              # 'England Premier League' : 'england/premier-league', 
              # 'England League 1'       : 'england/league-one',
              # 'England League 2'       : 'england/league-two',
               'France Ligue 1'         : 'france/ligue-1',
              # 'France Ligue 2'         : 'france/ligue-2',
               }    
    
dict_markets =  {
                '3way'    : '3-Way',
                'over2.5' : 'Over/Under', 
                'btts'    : 'Both Teams to Score'
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
accept = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="_evidon-accept-button"]')))
accept.click()


#loop through leagues
count = 0
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
        
    # TODO: Currently not changing dropdown boxes
    # Use the following code to change dd values (BEFORE getting dropdowns)
    # Current problem: Site does not allow the same selected value in different dds
    #first_dropdown = Select(dropdowns[0])
    #first_dropdown.select_by_visible_text(market)            
    dropdowns = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'SportHeader-styles-drop-down')))
    dropdown_markets = []
    for i in range(0, len(dropdowns)):
      dropdown_markets.append(Select(dropdowns[i]).first_selected_option.accessible_name)
    if not set(dict_markets.values()).issubset(set(dropdown_markets)):
      print(f"Not all configured markets {dict_markets.values()} are visible: {dropdown_markets}")
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
        curr_market_dd = dropdown_markets[i-2] if i-2 < len(dropdown_markets) else ''
        if num_odd_buttons < 2 or num_odd_buttons > 3 or curr_market_dd not in dict_markets.values():
          continue
                
        market = list(dict_markets.keys())[list(dict_markets.values()).index(curr_market_dd)] # key from value
        if num_odd_buttons == 3:
          odd_home, odd_draw, odd_away = odd_buttons[0].text, odd_buttons[1].text, odd_buttons[2].text
          print(f"      {market}: {odd_home}, {odd_draw}, {odd_away}")
        elif num_odd_buttons == 2:
          odd_home, odd_away = odd_buttons[0].text, odd_buttons[1].text
          print(f"      {market}: {odd_home}, {odd_away}")    
        else:      
          print(f"      Found no odds for {market}")                        
          
      
      continue                     

      # concat markets and make 1 dataframe per league (still inside for loop)
      df_list = []
      for market in dict_markets.keys():
        df_list.append(pd.DataFrame({'Dates':dict_odds[f'dates_{market}'], 'Teams':dict_odds[f'teams_{market}'], market:dict_odds[f'odds_{market}']}).set_index(['Teams', 'Dates'])) 
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
