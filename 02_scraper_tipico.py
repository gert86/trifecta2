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
               'Germany 2. Bundesliga'  :'germany/2-bundesliga',
              #  'Italy Serie A'          : 'italy/serie-a',
              #  'Italy Serie B'          : 'italy/serie-b',
              #  'Spain La Liga'          : 'spain/la-liga',
              #  'Spain Segunda Division' : 'spain/la-liga-2',
              #  'England Premier League' : 'england/premier-league', 
              #  'England League 1'       : 'england/league-one',
              #  'England League 2'       : 'england/league-two',
              #  'France Ligue 1'         : 'france/ligue-1',
              #  'France Ligue 2'         : 'france/ligue-2',
               }    
    
dict_markets =  {
                '3-way'                 : '3-Way',
                'over-under'            : 'Over/Under',           # todo: which amount?
                'double-chance'         : 'Double chance',
                'draw-no-bet'           : 'Draw no bet',
                'over-under-halftime'   : 'Halftime-Over/Under',  # todo: which amount?
                'handicap'              : 'Handicap'              # todo: which amount?
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
  df_data = pd.DataFrame(columns=['Dates', 'Teams'] + list(dict_markets.keys()))
  df_data = df_data.set_index(['Dates', 'Teams'])
  count = count + 1
  curr_loop_str = f"{league}"
  print(f"League {count} of {len(dict_leagues)}: {curr_loop_str}...")
  league_url_suffix = league_data

  try:        
    # navigate to subpage
    full_url = url + league_url_suffix
    driver.get(full_url)
    time.sleep(2)

    
    # init dropdown_markets
    dropdown_markets = []  # what dropdowns currently show      
    dropdowns = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'SportHeader-styles-drop-down')))
    num_dropdowns = len(dropdowns)
    for dropdown in dropdowns:
      dd_text = Select(dropdown).first_selected_option.accessible_name
      dropdown_markets.append(dd_text)

    remaining_markets = list(dict_markets.values())   # what dropdowns should be set to in the future
    while remaining_markets:
      # change dd boxes which show non-relevant markets to those of interest
      for i in range(num_dropdowns):
        dd_text = dropdown_markets[i]
        if dd_text in remaining_markets:
          remaining_markets.remove(dd_text)
          print(f"{dd_text} is already selected in dropdown #{i} - keep it")
        elif remaining_markets:
          new_text = remaining_markets.pop(0)
          dropdown_markets[i] = new_text
          print(f"Changing dropdown #{i} to {new_text}")
          Select(dropdowns[i]).select_by_visible_text(new_text)
          
            
      # get table and immediate children    
      table = driver.find_element(by=By.XPATH, value='//*[@id="app"]/main/main/section/div/div[1]/div/div/div')            
      children=table.find_elements(by=By.XPATH,value='./*')

      # children are a mix of dates (<div>) and cells containing game data (<a>). 
      # Need to be processed in order
      games_with_dates = []
      date_str = ''
      for child in children:
        if child.tag_name == 'div':
          try:
            if ',' in child.text:
              date_time_obj = datetime.datetime.strptime(child.text.split(',')[1].strip(), '%d.%m').replace(year=datetime.datetime.now().year)
              date_str = date_time_obj.strftime('%Y-%m-%d')            
          except:
            pass
        if child.tag_name == 'a':
          games_with_dates.append((child, date_str))

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

        if not date_str:
          date_str = date_str = datetime.datetime.today().strftime('%Y-%m-%d')

        start_time_str = child_divs[0].find_element(by=By.XPATH, value='.//*[@class="EventDateTime-styles-time EventDateTime-styles-no-date"]').text
        home_team = child_divs[1].find_elements(by=By.XPATH,value='.//*[@class="EventTeams-styles-team-title"]')[0].text
        away_team = child_divs[1].find_elements(by=By.XPATH,value='.//*[@class="EventTeams-styles-team-title"]')[1].text
        print(f"    {date_str} {start_time_str}: {home_team} vs. {away_team}")
        df_key = (date_str, home_team+'\n'+away_team)
        if not df_key in df_data.index:
          df_data.loc[df_key, :] = None
          
        odds_dict = {}
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
            odds_dict[market] = f"{odd_home}\n{odd_draw}\n{odd_away}"
          elif num_odd_buttons == 2:
            odd_home, odd_away = odd_buttons[0].text, odd_buttons[1].text
            print(f"      {market}: {odd_home}, {odd_away}")
            odds_dict[market] = f"{odd_home}\n{odd_away}"
          else:      
            print(f"      Found no odds for {market}")
            continue

        for market, odds in odds_dict.items():          
          df_data.at[df_key, market] = odds

    # clean data
    df_data = df_data.fillna('')
    df_data = df_data.replace('SUSPENDED\n', '', regex=True)
    df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # make date being a real datatime object
    df_data = df_data.reset_index()
    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
    df_data = df_data.set_index(['Dates', 'Teams'])

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
