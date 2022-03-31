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
url = 'https://sports.tipico.de/en/live/soccer'
outfile_name = './scraped/dict_tipico_live.pck'

# chromedriver options and init
options = Options()
options.headless = True
options.add_argument('window-size=1920x1080')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)
driver.maximize_window()

# click accept cookies
accept = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="_evidon-accept-button"]')))
accept.click()

# ------(use it only if necessary)------
# scroll down to the bottom to load all matches
# driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
# time.sleep(3) # wait until page has reloaded

#select values from dropdowns
dropdowns = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'SportHeader-styles-drop-down')))
first_dropdown = Select(dropdowns[0])
second_dropdown = Select(dropdowns[1])
third_dropdown = Select(dropdowns[2])
first_dropdown.select_by_visible_text('Both Teams to Score') #update 'Both teams to score?' -> 'Both Teams to Score'
second_dropdown.select_by_visible_text('Over/Under')
third_dropdown.select_by_visible_text('3-Way')

# go 2 levels upwards
box = driver.find_element(by=By.XPATH, value='//div[contains(@testid, "Program_UPCOMING")]')
sport_title = box.find_element(by=By.CLASS_NAME, value='SportTitle-styles-sport')
parent = sport_title.find_element(by=By.XPATH, value='./..')
grandparent = parent.find_element(by=By.XPATH, value='./..').find_element(by=By.XPATH, value='./..').find_element(by=By.XPATH, value='./..').find_element(by=By.XPATH, value='./..')

# find empty events 
try:
    empty_groups = grandparent.find_elements(by=By.CLASS_NAME, value='EventOddGroup-styles-empty-group')
    empty_events = [empty_group.find_element(by=By.XPATH, value='./..') for empty_group in empty_groups[:]]
except:
    pass

# handle single row events and remove empty events
single_row_events = grandparent.find_elements(by=By.CLASS_NAME, value='EventRow-styles-event-row')
try:    
    single_row_events = [single_row_event for single_row_event in single_row_events if single_row_event not in empty_events]
except:
    pass

# values to be filled
teams = []
x12 = []
btts = []
over_under = []
odds_events = []
for match in single_row_events:
    odds_event = match.find_elements(by=By.CLASS_NAME, value='EventOddGroup-styles-odd-groups')
    odds_events.append(odds_event)    
    for team in match.find_elements(by=By.CLASS_NAME, value='EventTeams-styles-titles'):  # teams
        teams.append(team.text)
for odds_event in odds_events:
    for n, box in enumerate(odds_event):
        rows = box.find_elements(by=By.XPATH, value='.//*')
        if n == 0:  # 3-way
            x12.append(rows[0].text)
        
        if n == 1:  # over/under + goal line (i.e. how many goals left until winning the bet)
            parent = box.find_element(by=By.XPATH, value='./..')
            goals = parent.find_element(by=By.CLASS_NAME, value='EventOddGroup-styles-fixed-param-text').text
            over_under.append(goals+'\n'+rows[0].text)
        
        if n == 2:  # both teams to score
            btts.append(rows[0].text)

driver.quit()

# set "unlimited" columns
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

#Storing lists within dict and further into data frame
dict_gambling = {'Teams': teams, 'btts': btts, 'Over/Under': over_under, '3-way': x12}
df_data = pd.DataFrame.from_dict(dict_gambling)
df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x) # clean whitespaces

#Save data with Pickle
output = open(outfile_name, 'wb')
pickle.dump(df_data, output)
output.close()
print(f"Done. Stored to {outfile_name}")

# WORKS