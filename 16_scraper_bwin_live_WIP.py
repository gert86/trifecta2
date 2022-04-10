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
url = 'https://sports.bwin.com/en/sports/live/football-4?fallback=false'
outfile_name = './scraped/dict_tipico_live.pck'

# chromedriver options and init
options = Options()
options.headless = True
options.add_argument('window-size=1920x1080')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(url)
driver.maximize_window()

teams = []
x12 = []
btts = []
over_under = [] 
odds_events = []

#switching dropdown
#option1
# time.sleep(2)
# dropdown = driver.find_elements_by_css_selector("div.title.multiple")
#option2
dropdown_1 = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="main-view"]/ms-live/ms-live-event-list/div/ms-grid/ms-grid-header/div/ms-group-selector[3]/ms-dropdown/div')))
dropdown_1.click()
dropdown_1.find_element(by=By.XPATH, value='//*[@id="main-view"]/ms-live/ms-live-event-list/div/ms-grid/ms-grid-header/div/ms-group-selector[3]/ms-dropdown/div[2]/div[10]').click()

box = driver.find_element(by=By.XPATH, value='//ms-grid[contains(@sortingtracking,"Live")]') #livebox
rows = WebDriverWait(box, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'grid-event')))

for row in rows:
    odds = row.find_elements(by=By.CLASS_NAME, value='grid-option-group')
    try:
        empty_events = row.find_elements(by=By.CLASS_NAME, value='empty') #removing empty odds
        odds = [odd for odd in odds if odd not in empty_events]
    except:
        pass
    for n, odd in enumerate(odds[:3]): #only the 3 first dropdowns
        if n==0:
            x12.append(odd.text)
            grandparent = odd.find_element(by=By.XPATH, value='./..').find_element(by=By.XPATH, value='./..')
            teams.append(grandparent.find_element(by=By.CLASS_NAME, value='grid-event-name').text)
        if n==1:
            over_under.append(odd.text)
        if n==2:
            btts.append(odd.text)

driver.quit()

#unlimited columns
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

dict_gambling = {'Teams':teams,'btts': btts,
                 'Over/Under': over_under, '3-way': x12}

df_data = pd.DataFrame.from_dict(dict_gambling)
df_data['Over/Under'] = df_data['Over/Under'].apply(lambda x:re.sub(',', '.', x))
df_data = df_data.applymap(lambda x: x.strip() if isinstance(x, str) else x)


#Save data with Pickle
output = open(outfile_name, 'wb')
pickle.dump(df_data, output)
output.close()

# TODO
