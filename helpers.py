import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import pickle
import datetime
import re
import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

# Note:
# An XPATH like '//*[@data-testid="odd-groups"]' is global (i.e. no matter on which element it's called)
# An XPATH like './/*[@data-testid="odd-groups"]' finds only the children of the element


# ---------------------------------------------------------------------------------------
class ChromeHelper:
  def __init__(self, url) -> None:
    # open chrome maximized with inspector opened at the bottom    
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    options.add_argument("--auto-open-devtools-for-tabs")
    prefs = {"devtools": 
        {"preferences": 
          {"panel-selectedTab": "\"elements\"",
          "currentDockState": "\"bottom\""
        }}}
    options.add_experimental_option(name="prefs", value=prefs)
    self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    self.openUrl(url)

  def openUrl(self, url):
    self.url = url
    self.driver.get(self.url)

# ---------------------------------------------------------------------------------------
class GraphHelper():
  def __init__(self) -> None:
    style.use('fivethirtyeight')
    self.fig = plt.figure()
    self.ax = self.fig.add_subplot(1,1,1)
    self.graph_data_array = []
    self.graph_title_info = ""
    self.interval_in_secs = 10

  @staticmethod
  def getLabels(market_name, odds_data):
    if market_name == '3-way':
      return ['1','X','2'] if len(odds_data)==3 else ['?']*len(odds_data)
    elif market_name == 'next-goal':
      return ['1','X','2'] if len(odds_data)==3 else ['?']*len(odds_data)
    elif market_name == 'btts':
      return ['Yes', 'No'] if len(odds_data)==2 else ['?']*len(odds_data)
    elif market_name == 'match-winner':
      return ['1', '2'] if len(odds_data)==2 else ['?']*len(odds_data)     
    elif market_name == 'set-winner':
      return ['1', '2'] if len(odds_data)==2 else ['?']*len(odds_data)  
    elif market_name == 'tie-break-yes-no':
      return ['Yes', 'No'] if len(odds_data)==2 else ['?']*len(odds_data)
    
  @staticmethod
  def getColors(odds_data):
    assert(len(odds_data) <= 3)
    return ['r','g','b','c','m','y'][0:len(odds_data)]
      
  def addData(self, event_name, market_name, odds_data):
    if not odds_data or len(odds_data) < 1:
      print(f"Found no odds for {market_name}: {Misc.removeNewline(event_name, ' vs. ')}")
      return

    if str(event_name).endswith("1st half"):
      event_name = event_name[0:str(event_name).find("1st half")]
      odds_data = odds_data[0:int(len(odds_data)/2)]
      print(f"Tweaked to {event_name} and {odds_data} -> score: {100*float(Misc.score([o for o in odds_data]))}")

    if len(odds_data) != len(self.graph_data_array):
      self.graph_data_array.clear()
      for i in range(len(odds_data)):
        self.graph_data_array.append([])
    
    curr_score = 100*float(Misc.score([o for o in odds_data]))
    title = f"{market_name}: {Misc.removeNewline(event_name, ' vs. ')} ({curr_score:.2f}%)"
    labels = GraphHelper.getLabels(market_name, odds_data)
    colors = GraphHelper.getColors(odds_data)
    self.ax.clear()
    self.ax.set_title(title)    
    x = [self.interval_in_secs * num for num in range(1 + len(self.graph_data_array[0]))]
    for i,graph_data in enumerate(self.graph_data_array):
      graph_data.append(odds_data[i])
      self.ax.plot(x, self.graph_data_array[i], label=labels[i] + f" ({odds_data[i]})", color=colors[i])
    self.ax.legend()

    # Show surebet border
    if len(odds_data) == 2:    
      surebet_odd_0 = odds_data[1]/(odds_data[1]-1.0)
      self.ax.axhline(y=surebet_odd_0, linestyle="--", color=colors[0], linewidth=0.5)
      surebet_odd_1 = odds_data[0]/(odds_data[0]-1.0)
      self.ax.axhline(y=surebet_odd_1, linestyle="--", color=colors[1], linewidth=0.5) 
      print(f"Surebet odds: {surebet_odd_0} and {surebet_odd_1}")

# ---------------------------------------------------------------------------------------
class BookieHelperBase:
  def __init__(self, url, dict_markets) -> None:
    if not url:
      raise Exception(f"url must not be empty")    
    if not dict_markets:
      raise Exception(f"Market dict must not be empty")
    
    self.chrome_hlp = ChromeHelper(url)
    self.driver = self.chrome_hlp.driver
    self.dict_markets = dict_markets
    self.graph_hlp = None
    self.table = None
    self.events = []
    self.dd_index_mapping = {}
    self.scraped_dict = {}

  def saveToFile(self, outfile_name):
    if not outfile_name:
      print("Saving failed. No output file name provided.")
      return
    
    output = open(outfile_name, 'wb')
    pickle.dump(self.scraped_dict, output)
    output.close()
    print(f"Done. Stored to {outfile_name}")    

# ---------------------------------------------------------------------------------------
class TipicoHelper(BookieHelperBase):

  def acceptCookies(self):
    accept = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="_evidon-accept-button"]')))
    accept.click()

  def findEventsTable(self, live):
    if live:
      self.table = WebDriverWait(self.driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, '//*[@testid="Program_LIVE"]')))[0]    
      self.events = self.table.find_elements(by=By.XPATH, value='.//*[@data-gtmid="eventRowContainer"]')
    else:
      self.table = WebDriverWait(self.driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, '//*[@testid="Program_SELECTION"]')))[0] 
      self.events = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, './/div[@data-testid="competition-events"]')) )
          
  def setDropdowns(self):
    dropdowns = self.table.find_elements(by=By.CLASS_NAME, value='SportHeader-styles-drop-down')
    if len(dropdowns) < len(self.dict_markets):
      raise Exception(f"Expecting at least {len(self.dict_markets)} dropdowns but found {len(dropdowns)}. Exit!")

    # set dropdowns to cover all markets
    dropdown_selected_texts = [Select(dd).first_selected_option.accessible_name for dd in dropdowns] 
    remaining_markets = list(self.dict_markets.values())   # what dropdowns should be set to in the future

    # change dropdowns that show non-relevant market to those of interest
    # only change them if market of interest isn't present anywhere else (no duplicates allowed)
    self.dd_index_mapping = {}
    while remaining_markets:
      for i,dd_text in enumerate(dropdown_selected_texts):
        if dd_text in remaining_markets:
          remaining_markets.remove(dd_text)
          print(f"Dropdown #{i} -> keep {dd_text}.")
          self.dd_index_mapping[dd_text] = i
        elif remaining_markets:
          for r in remaining_markets:
            if r in dropdown_selected_texts:
              pass
              print(f"Dropdown #{i} -> change to {r} not possible (exists already), try changing to a different one...")
            else:
              new_text = r
              remaining_markets.remove(new_text)
              dropdown_selected_texts[i] = new_text
              print(f"Dropdown #{i} -> changed to {new_text}.")
              Select(dropdowns[i]).select_by_visible_text(new_text)
              self.dd_index_mapping[new_text] = i
              break   # next dd

    # verify dropdown 
    dropdowns = self.table.find_elements(by=By.CLASS_NAME, value='SportHeader-styles-drop-down') # update
    for dd_text, idx in self.dd_index_mapping.items():
      assert(dd_text == Select(dropdowns[idx]).first_selected_option.accessible_name)


  def fetchAllMarketOdds(self, league_name):
    df_data = pd.DataFrame(columns=['Dates', 'Teams'] + list(self.dict_markets.keys()))
    df_data = df_data.set_index(['Dates', 'Teams'])
    self.findEventsTable(live=False)    

    children = self.events.find_elements(by=By.XPATH,value='./*')
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
    
    for game,date_str in games_with_dates:
      try:
        if not date_str:
          date_str = date_str = datetime.datetime.today().strftime('%Y-%m-%d')
        start_time_str = game.find_element(by=By.XPATH, value='.//*[@class="EventDateTime-styles-time EventDateTime-styles-no-date"]').text
        home_team = game.find_elements(by=By.XPATH, value='.//*[@class="EventTeams-styles-team-title"]')[0].text
        away_team = game.find_elements(by=By.XPATH, value='.//*[@class="EventTeams-styles-team-title"]')[0].text
        #print(f"    {date_str} {start_time_str}: {home_team} vs. {away_team}")
        df_key = (date_str, home_team+'\n'+away_team)
        if not df_key in df_data.index:
          df_data.loc[df_key, :] = None

        odds_children = game.find_elements(by=By.XPATH, value='.//div[@class="EventOddGroup-styles-odd-groups"]')
        for market,dd_idx in self.dd_index_mapping.items():
          odds = odds_children[dd_idx].text
          if market == 'double-chance':
            try:
              odd_list = odds.split('\n')
              odds = '\n'.join([odd_list[0], odd_list[2], odd_list[1]])   # unify to 1X, 2X, 12
            except:
              odds = ''
          df_data.at[df_key, market] = odds
          #print(f"        {market}: {Misc.removeNewline(odds)}")     
      except:
        continue

    # clean data
    df_data = df_data.fillna('')
    df_data = df_data.replace('SUSPENDED\n', '', regex=True)
    df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # make date being a real datatime object
    df_data.reset_index(inplace=True)
    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))
    df_data = df_data.set_index(['Dates', 'Teams'])

    #storing dataframe of each league in dictionary
    self.scraped_dict[league_name] = df_data
    print(f"Finished {league_name} -> Found {len(self.scraped_dict[league_name])} games\n\n")
    
  def fetchLiveEvents(self):
    self.findEventsTable(live=True)    
    self.event_teams = []
    for event in self.events:
      event_team_name = event.find_element(by=By.XPATH, value='.//*[@data-gtmid="teamNames"]').text
      self.event_teams.append(event_team_name)
          
  def requestLiveFilters(self):
    # Let the user choose the event and market to watch
    market_keys = list(self.dict_markets.keys())
    print(f"\nChoose the event: ")
    for n_event, event_team in enumerate(self.event_teams):
      print(f"{n_event}: {Misc.removeNewline(event_team)}")
    inputEvent = input(f"Enter a value between 0 and {len(self.event_teams) - 1}: ")

    print(f"\nChoose the market: ")
    for n_market, key in enumerate(market_keys):
      print(f"{n_market}: {self.dict_markets[key]}")
    inputMarket = input(f"Enter a value between 0 and {len(market_keys) - 1}: ")

    event_filter = self.event_teams[int(inputEvent)]
    market_filter = market_keys[int(inputMarket)]

    print(f"\nYour selection:\nEvent: {Misc.removeNewline(event_filter)}"
      f"\nMarket: {self.dict_markets[market_filter] if market_filter is not None else 'N/A' }")
    
    return event_filter, market_filter

  def fetchLivePeriodic(self, event_filter, market_filter, interval_in_secs):
    self.event_filter_live = event_filter
    self.market_filter_live = market_filter
    self.graph_hlp = GraphHelper()
    self.graph_hlp.interval_in_secs = interval_in_secs
    ani = animation.FuncAnimation(fig=self.graph_hlp.fig, func=self.__animate__, interval=1000*self.graph_hlp.interval_in_secs)
    plt.show()
    self.driver.quit()

  # private stuff
  def __fetchLive__(self):
    self.findEventsTable(live=True)
    self.event_teams = []
    for event in self.events:
      event_team_name = event.find_element(by=By.XPATH, value='.//*[@data-gtmid="teamNames"]').text
      self.event_teams.append(event_team_name)

    # get requested odds from requested team
    for event in self.events:
      event_teams = event.find_element(by=By.XPATH, value='.//*[@data-gtmid="teamNames"]')
      if event_teams.text != self.event_filter_live:
        continue
      print(f"Found requested event: {Misc.removeNewline(event_teams.text)}")
      try:
        event_odds_element = event.find_elements(by=By.XPATH, value='.//*[@data-testid="odd-groups"]')
        idx = self.dd_index_mapping[ self.dict_markets[self.market_filter_live] ]
        event_odds = event_odds_element[idx].text
        curr_odds = [round(float(v),2) for v in event_odds.split("\n")]
        return curr_odds
      except Exception:
        print(f"Could not find odds for requested market {self.market_filter_live}")
        return None

  # update live plot of watched game/market
  def __animate__(self, i): 
    odds_data_live = self.__fetchLive__()
    self.graph_hlp.addData(self.event_filter_live, self.market_filter_live, odds_data_live)



# ---------------------------------------------------------------------------------------
class BetfairHelper(BookieHelperBase):

  def acceptCookies(self):
    try:
      time.sleep(2)
      accept = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')))         
      accept.click()
    except:
      pass

  def setLanguageEnglish(self):
    language_box = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'ssc-hlsw')))
    WebDriverWait(language_box, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ssc-hls'))).click()
    WebDriverWait(language_box, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ssc-en_GB'))).click()
    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Over/Under 2.5 Goals")]')))

  def navigateToLeague(self, league_data,):
    #print(f"League {count} of {len(dict_leagues)}: {curr_loop_str}...")
    country, league_id = league_data
    try:    
      # click on competitions
      header = self.driver.find_element(by=By.CLASS_NAME, value='updated-competitions')
      competition = WebDriverWait(header, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@title, "COMPETITIONS")]')))
      competition.click()

      # click on countries button (e.g. "German Football")
      competitions_table = WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, 'mod-multipickazmenu-1056')))
      country_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/div[contains(@data-category,' +'"' + country + '"' + ')]')))
      country_button.click() 

      # click on country's league button (e.g. "German Bundesliga")
      league_button = WebDriverWait(competitions_table, 5).until(EC.element_to_be_clickable((By.XPATH, './/a[contains(@data-galabel,' +'"' + league_id + '"' + ')]')))
      league_button.click()
    except Exception as e:
      print(f"\n\nException in {league_id}: {str(e)}\n\n")

  def findEventsTableAndFetch(self, live, league_name):
    if live:
      raise Exception("Betfail Live not implemented!")
    
    dict_odds = {}
    for market, market_data in self.dict_markets.items():
      list_dates = []
      list_teams = []
      list_odds = []

      # 3-way has its own column without a drop down box, for others change the dropdown value
      if market != '3-way':        
        dropdown = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'marketchooser-container')))
        dropdown.click()
        chooser = WebDriverWait(dropdown, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[contains(text(),'+'"'+str(market_data)+'"'+')]')))
        chooser.click()
        time.sleep(1)  

      games = WebDriverWait(self.driver, 5).until(EC.visibility_of_all_elements_located((By.CLASS_NAME, 'event-information')))              
      for game in games:
        try:
          date_time_str = game.find_element(by=By.XPATH, value='.//*[@class="date ui-countdown"]').text
          list_dates.append(date_time_str)
        except:
          continue        

        if market == '3-way':
          odds = game.find_elements(by=By.XPATH, value=f'.//div[@class="details-market market-3-runners"]')[-1]
        elif market == 'double-chance':
          odds = game.find_elements(by=By.XPATH, value=f'.//div[@class="details-market market-3-runners"]')[0]
        else:
          odds = game.find_element(by=By.XPATH, value=f'.//div[@class="details-market market-2-runners"]')
        list_odds.append(odds.text)
        
        teams_container = game.find_element(by=By.CLASS_NAME, value='teams-container').text
        list_teams.append(teams_container)
      
      #storing 1 data dict per market
      dict_odds[f'dates_{market}'] = list_dates        
      dict_odds[f'teams_{market}'] = list_teams
      dict_odds[f'odds_{market}']  = list_odds

    # concat dicts and make 1 dataframe per league (still inside for loop)
    df_list = []
    for market in self.dict_markets.keys():
      df_list.append(pd.DataFrame({'Dates':dict_odds[f'dates_{market}'], 'Teams':dict_odds[f'teams_{market}'], market:dict_odds[f'odds_{market}']}).set_index(['Teams', 'Dates'])) 
    df_data = pd.concat(df_list, axis=1, sort=True)            
    df_data.reset_index(inplace=True)
    #df_data.rename(columns={'index':'Teams'}, inplace=True)

    # clean data
    df_data = df_data.fillna('')
    df_data = df_data.replace('SUSPENDED\n', '', regex=True)
    df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # replace words "In-Play", "Today" and "Tomorrow" with numeric dates or add date if missing
    today = datetime.datetime.today()
    tomorrow = today + datetime.timedelta(days=1)
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('In-Play', today.strftime("%d %b"), x))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Today', today.strftime("%d %b"), x))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('Tomorrow', tomorrow.strftime("%d %b"), x))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: re.sub('^[0-2][0-9]:[0-5][0-9]$', today.strftime("%d %b") + ' ' + x, x))    
    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(str(today.year) + ' ' + x, '%Y %d %b %H:%M'))
    df_data['Dates'] = df_data['Dates'].apply(lambda x: datetime.datetime.strptime(str(x.date()), '%Y-%m-%d'))
    df_data.set_index(['Dates', 'Teams'], inplace=True)

    self.scraped_dict[league_name] = df_data
    print(f"Finished {league_name} -> Found {len(self.scraped_dict[league_name])} games\n\n")    


# ---------------------------------------------------------------------------------------
# general purpose helper functions
class Misc:
  @staticmethod
  def score(vals):
    val = 1.0/((1.0/np.asarray(vals)).sum())
    return f"{val:.4f}"

  @staticmethod
  def removeNewline(text, sep=' ; '):
    nl = '\n' 
    return str(text).replace(nl, sep)
  
  @staticmethod
  def printOdds(oddStr, inSep="\n", outSep=" / "):
    odd_splitted = oddStr.split(inSep)
    ret = ""
    for odd in odd_splitted:
      ret += odd + outSep

