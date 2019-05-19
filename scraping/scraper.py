from sqlalchemy import create_engine
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
import time
import datetime as dt
from datetime import datetime
import calendar
import os
import sys

# give access to the parent directory to run independently
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'dineinhall'))
try:
    SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]  # URI from Heroku
except Exception:
    from creds import SQLALCHEMY_DATABASE_URI  # local URI

# allows us to recreate SQL query statements in Python
engine = create_engine(SQLALCHEMY_DATABASE_URI)

browser = webdriver.Chrome('/chromedriver')
browser.get('https://new.dineoncampus.com/Northeastern/menus')
time.sleep(5)  # wait for page to render javascript
soup = BeautifulSoup(browser.page_source, 'lxml')

import linecache
import sys

# method to print exception with line numbers
def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print(f'EXCEPTION IN ({filename}, LINE {lineno} "{line.strip()}"): {exc_obj}')


class Utils():

    # fetches any field from the last row of the database
    def fetchLastField(self, field):
        with engine.connect() as con:
            rs = con.execute(f'select distinct {field} '
                              'from menu join food_on_menu using (menu_id) '
                              'join food using (food_id) '
                             f'order by {field} desc '
                              'limit 1')
        # returns the first item in the row
        try:
            return list(rs)[0][0]
        except IndexError:
            return 0

    # creates a list of dictionaries with any variable amount of fields for the dictionary
    def createCombinations(self, *args):
        final_list = []
        with engine.connect() as con:
            rs = con.execute(f'select distinct * '
                              'from menu join food_on_menu using (menu_id) '
                              'join food using (food_id)')
            # for each row in the result
            for row in rs:
                dict = {}
                # create a key value pair for each columnn
                for column in args:
                    dict[column] = row[column]
                final_list.append(dict)
            # insert a sentinel value to create a dictionary if no previous data exists
            final_list.append({'sentinel': -1})
        return final_list

    def cleanName(self, foodName):
        foodName = foodName.replace("%", r"%%")
        foodName = foodName.replace('"', r"'")
        return foodName


class Scraper():
    def __init__(self, browser, soup):
        self.browser = browser
        self.soup = BeautifulSoup(browser.page_source, 'lxml')
        # sets the food id to the last known food id
        self.foodID = Utils().fetchLastField('food_id')
        # sets the menu id to the last known menu id
        self.menuID = Utils().fetchLastField('menu_id')
        # list of dictionary combinations of food ids and their associated names
        self.uniqueFoods = Utils().createCombinations('food_id', 'food_name')
        # list of dictionary combinations of unique menu data
        self.uniqueMenus = Utils().createCombinations('meal_type', 'location', 'menu_date')
        # list of dictionary pairs of menu ids and food ids
        self.uniqueMenuFoodCombo = Utils().createCombinations('menu_id', 'food_id')

    # strips the nutrient information of all characters except digits and decimals
    def stripNutrients(self, element):
        result = ''.join(c for c in element if c.isdigit() or c == '.')
        # returns a None if the value does not exist else return the result
        return 'NULL' if result == '' else result

    # scrapes NU menu and inserts into food, menu, and food_on_menu tables in database
    def insertData(self, location, mealType, date):
        # gets the active tables
        activeTable = self.soup.find('div', class_=['tab-pane', 'show', 'fade', 'active'])
        # gets every section in the menu
        tables = activeTable.findAll('table', class_=['menu-items', 'table', 'b-table', 'b-table-stacked-md'])
        for table in tables:
            # gets each item row in the section
            tableRows = table.findAll('tr')
            for row in tableRows:
                # gets all the strong tags from the possible rows
                itemName = row.findAll('strong')
                if itemName:
                    # gets the food name
                    foodName = Utils().cleanName(itemName[0].text.strip())
                    # goes to the div with the image links
                    special = row.findAll('td')[1].div
                    src_links = []
                    # goes through every image in the div
                    for image in special.findAll('img'):
                        # creates a list of image src links
                        src_links.append(image['src'])
                    # assigns food qualities based on whether the image links are present for that food item
                    vegetarian = "/img/icon_vegetarian_200px.png" in src_links
                    vegan = "/img/icon_vegan_200px.png" in src_links
                    balanced = "/img/icon_balanced_200px.png" in src_links
                    # gets the serving sizes for each food item
                    serving = row.findAll('td')[2].div.text
                    # iterates through each food item
                    for item in itemName:
                        # gets the nutritional div for the food item
                        nutritionalDiv = row.find('div', class_='modal-body')
                        # gets all the nutritional information list items
                        nutritionalListElements = nutritionalDiv.findAll('li')
                        # assigns all the nutritional information accordinly while stripping all but numbers and decimals
                        calories = self.stripNutrients(nutritionalListElements[0].text)
                        caloriesFromFat = self.stripNutrients(nutritionalListElements[1].text)
                        cholesterol = self.stripNutrients(nutritionalListElements[2].text)
                        dietaryFiber = self.stripNutrients(nutritionalListElements[3].text)
                        protein = self.stripNutrients(nutritionalListElements[4].text)
                        saturatedFat = self.stripNutrients(nutritionalListElements[5].text)
                        sodium = self.stripNutrients(nutritionalListElements[6].text)
                        sugar = self.stripNutrients(nutritionalListElements[7].text)
                        totalCarbs = self.stripNutrients(nutritionalListElements[8].text)
                        totalFat = self.stripNutrients(nutritionalListElements[9].text)
                        transFat = self.stripNutrients(nutritionalListElements[10].text)
                        vitaminD = self.stripNutrients(nutritionalListElements[11].text)

                    # writes to the database
                    newMenuAttributes = {'meal_type': mealType, 'location': location, 'menu_date': date}
                    # if this menu has not been recorded yet
                    if newMenuAttributes not in self.uniqueMenus:
                        self.menuID += 1
                        # add the combination of attributes to the list of dictionaries
                        self.uniqueMenus.append(newMenuAttributes)

                        # insert into menu table in database
                        with engine.begin() as con:
                            con.execute("INSERT INTO menu "
                                        "(menu_id, meal_type, location, menu_date) "
                                       f'VALUES ({self.menuID}, "{mealType}", "{location}", "{date}")')

                    existingFoodNames = [d.get('food_name', None) for d in self.uniqueFoods]
                    # if this food item has not been recorded yet
                    if foodName not in existingFoodNames:
                        self.foodID += 1
                        # add the combination of attributes to the list of dictionaries
                        self.uniqueFoods.append({'food_id': self.foodID, 'food_name': foodName})

                        # insert into food table in database
                        print(foodName)
                        with engine.begin() as con:
                            con.execute("INSERT INTO food "
                                        "(food_id, food_name, serving, calories, calories_from_fat, "
                                        "cholesterol, dietary_fiber, protein, saturated_fat, sodium, "
                                        "sugar,total_carbs, total_fat, trans_fat, vitamin_d, vegetarian, "
                                        "vegan, balanced) "
                                       f'VALUES ({self.foodID}, "{foodName}", "{serving}", {calories}, {caloriesFromFat}, '
                                       f'{cholesterol}, {dietaryFiber}, {protein}, {saturatedFat}, {sodium}, {sugar}, '
                                       f'{totalCarbs}, {totalFat}, {transFat}, {vitaminD}, {vegetarian}, {vegan}, {balanced})')

                        # prints out all the scraped data
                        print('NEW', self.foodID, foodName, serving, calories, caloriesFromFat, cholesterol, dietaryFiber, protein, saturatedFat,
                              sodium, sugar, totalCarbs, totalFat, transFat, vitaminD, vegetarian, vegan, balanced, location, mealType, date)

                        # make a dictionary with the menuID and the new foodID
                        newMenuFoodCombo = {'menu_id': self.menuID, 'food_id': self.foodID}
                        # add the combination of attributes to the list of dictionaries
                        self.uniqueMenuFoodCombo.append(newMenuFoodCombo)

                        # insert into food_on_menu table in database
                        with engine.begin() as con:
                            con.execute("INSERT INTO food_on_menu "
                                        "(menu_id, food_id) "
                                       f"VALUES ({self.menuID}, {self.foodID})")
                    # if this food item has already been recorded
                    else:
                        dict = self.uniqueFoods[existingFoodNames.index(foodName)]
                        print('EXISTS', foodName, dict, location, mealType, date)
                        # make a dictionary with the menuID and the foodID referencing the recorded food
                        newMenuFoodCombo = {'menu_id': self.menuID, 'food_id': dict['food_id']}
                        # if this is a new combination then record in the database
                        if newMenuFoodCombo not in self.uniqueMenuFoodCombo:
                            self.uniqueMenuFoodCombo.append(newMenuFoodCombo)

                            # insert into food_on_menu table in database
                            with engine.begin() as con:
                                con.execute("INSERT INTO food_on_menu "
                                            "(menu_id, food_id) "
                                           f"VALUES ({self.menuID}, {dict['food_id']})")

    # waits for page to load within the given limit before scraping data
    def waitForTab(self, limit):
        try:
            start = time.time()  # start time
            end = start
            loading_msg = self.browser.find_element_by_css_selector('div.loading-content_loadingText_22OQi').get_attribute('textContent').strip()
            wait_msg = "Loading menus for selected location and date"
            failure_msg = "Sorry, we weren't able to find menus for this location for the day you selected."
            # while page is loading
            while(loading_msg == wait_msg or loading_msg == failure_msg):
                # update the end time to be the current time
                end = time.time()
                # if the limit has been passed and the failure message appears no foods exist so break
                if ((end-start)//1 >= limit and loading_msg == failure_msg):
                    break
                # else wait for 0.1 more seconds
                else:
                    time.sleep(0.1)
                loading_msg = self.browser.find_element_by_css_selector('div.loading-content_loadingText_22OQi').get_attribute('textContent').strip()
        except Exception:
            pass

    # scrapes NU menu and tries to iterate through each day and location of the menu
    def tryInserting(self, date):
        locations = ['Stwest', 'IV', 'Steast']
        mealTypes = ['Breakfast', 'Lunch', 'Dinner']
        searchBarLocations = ['Food Hall at Stetson West', 'International Village', 'Levine Marketplace']
        for location in locations:
            currentLocation = browser.find_element_by_css_selector('div.dropdown.v-select.single.searchable.location-dropdown_menuLocationDropdown_58tYo')
            currentLocation = currentLocation.find_element_by_css_selector('span.selected-tag').get_attribute('textContent').strip()
            searchBarText = searchBarLocations[locations.index(location)]
            if searchBarText != currentLocation:
                searchBar = browser.find_element_by_css_selector('input.form-control')
                searchBar.send_keys(searchBarText)
                searchBar.send_keys(Keys.ENTER)
            for tabName in mealTypes:
                try:
                    self.waitForTab(3)
                    tab = self.browser.find_element_by_link_text(tabName)
                    tab.click()
                    self.soup = BeautifulSoup(self.browser.page_source, 'lxml')
                    self.insertData(location, tabName, date)
                except NoSuchElementException:
                    print(f"Couldn't find {tabName} for {location} on {date}")

    # scrape all the data from the website
    def scrapeAll(self):
        dayButtons = self.browser.find_elements_by_css_selector('div.day-wrapper.col')
        nextButton = self.browser.find_element_by_css_selector('div.col-menu-calendar-next.col')
        month = dayButtons[0].find_element_by_css_selector('div.menu-calendar_month_3MA76').get_attribute('textContent').strip()
        date = dayButtons[0].find_element_by_css_selector('div.menu-calendar_day_1Rsn-').get_attribute('textContent').strip()
        monthNum = list(calendar.month_name).index(month)
        year = int(datetime.now().strftime('%Y'))
        fullDate = dt.datetime(year, monthNum, int(date))
        # stop scraping after a week
        days = 0
        while(days != 7):
            for day in dayButtons:
                if (days != 7):
                    shortDate = fullDate.strftime('%Y-%m-%d')
                    day.click()
                    self.waitForTab(3)
                    self.tryInserting(shortDate)
                    # increment the date by 1 day
                    fullDate += dt.timedelta(days=1)
                    days += 1
                else:
                    break
            nextButton.click()


scraper = Scraper(browser, soup)  # scraper object
# initiate the scraping of all data
scraper.scrapeAll()
