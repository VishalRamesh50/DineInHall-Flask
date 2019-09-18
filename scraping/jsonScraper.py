from sqlalchemy import create_engine
import datetime as dt
from datetime import datetime
from pytz import timezone
import json
import urllib.request
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


class Utils():

    # fetches any field from the last row of the database
    def fetchLastField(self, field):
        with engine.connect() as con:
            rs = con.execute(f'select distinct {field} '
                             'from food left join food_on_menu using (food_id) '
                             'left join menu using (menu_id) '
                             'left join food_on_allergen using (food_id) '
                             'left join allergen using (allergen_id) '
                             f'order by {field} desc '
                             'limit 1')
        # returns the first item in the row
        try:
            item = list(rs)[0][0]
            return item if item is not None else 0
        except IndexError:
            return 0

    # creates a list of dictionaries with any variable amount of fields for the dictionary
    def createCombinations(self, *args):
        final_list = []
        with engine.connect() as con:
            rs = con.execute(f'select distinct * '
                             'from food left join food_on_menu using (food_id) '
                             'left join menu using (menu_id) '
                             'left join food_on_allergen using (food_id) '
                             'left join allergen using (allergen_id)')
            # for each row in the result
            for row in rs:
                dict = {}
                # create a key value pair for each columnn
                for column in args:
                    dict[column] = row[column]
                # to avoid filler data
                if not all(value is None for value in dict.values()):
                    final_list.append(dict)
        return final_list

    def cleanStringNames(self, foodName):
        foodName.strip()
        # replace % with %% to insert into SQL queries
        foodName = foodName.replace("%", r"%%")
        # escape apostrophes to insert into SQL queries
        foodName = foodName.replace('"', r"\"")
        return foodName

    def cleanNutrientName(self, nutrientName):
        # remove everything after the first parentheses and strip white space
        nutrientName = nutrientName.split('(')[0].strip()
        # replace all the spaces with underscores and convert to lowercase
        nutrientName = nutrientName.lower().replace(' ', '_')
        # shorten carbohydrates to an acronym
        if nutrientName == 'total_carbohydrates':
            nutrientName = 'total_carbs'
        return nutrientName

    # strips the nutrient information of all characters except digits and decimals
    def stripNutrient(self, element):
        result = ''.join(c for c in str(element) if c.isdigit() or c == '.')
        # returns a null if the value does not exist else return the result
        return 'NULL' if result == '' else result


class Scraper():
    def __init__(self):
        # location IDs for the API
        self.stwestID = "5b9bd1c41178e90d4774210e"
        self.steastID = "586d05e4ee596f6e6c04b527"
        self.ivID = "586d17503191a27120e60dec"
        self.locations = ['Stwest', 'IV', 'Steast']
        self.locationIDs = [self.stwestID, self.ivID, self.steastID]
        # sets each variable to the last known id
        self.foodID = Utils().fetchLastField('food_id')
        self.menuID = Utils().fetchLastField('menu_id')
        self.allergenID = Utils().fetchLastField('allergen_id')
        print("Food ID:", self.foodID, "Menu ID:", self.menuID, "Allergen ID:", self.allergenID)
        # creates a list of dictionaries with the given attributes
        self.uniqueFoods = Utils().createCombinations('food_id', 'food_name')
        self.uniqueMenus = Utils().createCombinations('meal_type', 'location', 'menu_date')
        self.uniqueMenuFoodCombos = Utils().createCombinations('menu_id', 'food_id')
        self.uniqueAllergens = Utils().createCombinations('allergen_id', 'allergen_name')
        self.uniqueFoodAlergenCombos = Utils().createCombinations('food_id', 'allergen_id')
        # lists to keep track of new data
        self.newFoods = []
        self.newMenus = []
        self.newFoodMenuCombos = []
        self.newAllergens = []
        self.newFoodAllergenCombos = []

    # get data from API
    def getData(self, location, date):
        location_id = self.locationIDs[self.locations.index(location)]
        link = f"https://api.dineoncampus.com/v1/location/menu?site_id=5751fd2b90975b60e048929a&platform=0&location_id={location_id}&date={date}"
        with urllib.request.urlopen(link) as url:
            data = json.loads(url.read().decode())
            if data['status'] == 'success':
                menu = data['menu']  # type: dict

                # for each meal type (breakfast, lunch, dinner)
                for period in menu['periods']:
                    mealType = period['name']  # meal type
                    # for each category of the period
                    for category in period['categories']:
                        # categoryName = category['name']
                        # for each food item in the category
                        for food in category['items']:
                            foodData = {}

                            foodName = food['name'].strip()
                            foodData['food_name'] = foodName

                            calories = Utils().stripNutrient(food['calories'])
                            foodData['calories'] = calories

                            description = food['desc']
                            foodData['description'] = f'"{description}"' if description is not None else 'NULL'

                            allergens = []
                            filters = food['filters']  # array
                            # if no filters exist default the values to false
                            if len(filters) == 0:
                                foodData['vegetarian'] = False
                                foodData['vegan'] = False
                                foodData['balanced'] = False
                            for filt in filters:
                                filterName = filt['name']
                                filterType = filt['type']
                                if filterType == 'allergen':
                                    allergens.append(filterName.strip('*'))
                                foodData['vegetarian'] = (filterName == 'Vegetarian'
                                                          or foodData.get('vegetarian', False))
                                foodData['vegan'] = (filterName == 'Vegan'
                                                     or foodData.get('vegan', False))
                                foodData['balanced'] = (filterName == 'Balanced U'
                                                        or foodData.get('balanced', False))

                            nutrients = food['nutrients']  # array
                            for nutrient in nutrients:
                                nutrientName = nutrient['name']
                                nutrientValue = nutrient['value']
                                # nutrientUOM = nutrient['uom']
                                foodData[Utils().cleanNutrientName(nutrientName)] = Utils().stripNutrient(nutrientValue)

                            portion = food['portion']
                            foodData['serving'] = portion

                            existingAllergenNames = [d.get('allergen_name', None) for d in self.uniqueAllergens]
                            for allergen in allergens:
                                if allergen not in existingAllergenNames:
                                    self.allergenID += 1
                                    allergenDict = {'allergen_id': self.allergenID, 'allergen_name': allergen}
                                    self.uniqueAllergens.append(allergenDict)
                                    self.newAllergens.append(allergenDict)

                            newMenuAttributes = {'meal_type': mealType, 'location': location, 'menu_date': datetime.date(datetime.strptime(date, '%Y-%m-%d'))}
                            # if the menu is a new one
                            if newMenuAttributes not in self.uniqueMenus:
                                self.menuID += 1
                                self.uniqueMenus.append(newMenuAttributes)
                                fullMenuAttributes = newMenuAttributes.copy()
                                fullMenuAttributes['menu_id'] = self.menuID
                                self.newMenus.append(fullMenuAttributes)

                            existingFoodNames = [d.get('food_name', None) for d in self.uniqueFoods]
                            # if the food name is a new one
                            if (foodData['food_name'] not in existingFoodNames):
                                self.foodID += 1
                                foodData['food_id'] = self.foodID
                                self.newFoods.append(foodData)
                                self.uniqueFoods.append(foodData)
                                self.newFoodMenuCombos.append({'menu_id': self.menuID, 'food_id': self.foodID})
                                existingAllergenNames = [d.get('allergen_name', None) for d in self.uniqueAllergens]
                                for allergen in allergens:
                                    dict = self.uniqueAllergens[existingAllergenNames.index(allergen)]
                                    self.newFoodAllergenCombos.append({'food_id': self.foodID, 'allergen_id': dict['allergen_id']})
                            # if the food name exists
                            else:
                                dict = self.uniqueFoods[existingFoodNames.index(foodData['food_name'])]
                                # make a dictionary with the menuID and the foodID referencing the recorded food
                                newMenuFoodCombo = {'menu_id': self.menuID, 'food_id': dict['food_id']}
                                if newMenuFoodCombo not in self.uniqueMenuFoodCombos:
                                    self.uniqueMenuFoodCombos.append(newMenuFoodCombo)
                                    self.newFoodMenuCombos.append(newMenuFoodCombo)
                print(f"Got data for {location} on {date}")
            else:
                print(f"No data found for {location} on {date}")

    # insert data into food table
    def insertFoodData(self):
        if (len(self.newFoods) > 0):
            foodValues = ""
            for foodDict in self.newFoods:
                foodName = Utils().cleanStringNames(foodDict['food_name'])
                description = Utils().cleanStringNames(foodDict['description'])
                foodValues += (f'({foodDict["food_id"]}, "{foodName}", '
                               f'"{foodDict["serving"]}", {foodDict["calories"]}, '
                               f'{foodDict["calories_from_fat"]}, {foodDict["cholesterol"]}, '
                               f'{foodDict["dietary_fiber"]}, {foodDict["protein"]}, '
                               f'{foodDict["saturated_fat"]}, {foodDict["sodium"]}, '
                               f'{foodDict["sugar"]}, {foodDict["total_carbs"]}, '
                               f'{foodDict["total_fat"]}, {foodDict["trans_fat"]}, '
                               f'{foodDict["vitamin_d"]}, {foodDict["vegetarian"]}, '
                               f'{foodDict["vegan"]}, {foodDict["balanced"]}, '
                               f'"{description}"), \n')
            foodValues = foodValues[:-3]
            with engine.begin() as con:
                con.execute("INSERT INTO food "
                            "(food_id, food_name, serving, calories, calories_from_fat, "
                            "cholesterol, dietary_fiber, protein, saturated_fat, sodium, "
                            "sugar, total_carbs, total_fat, trans_fat, vitamin_d, vegetarian, "
                            "vegan, balanced, description) VALUES "
                            f'{foodValues}')

    # insert data into menu table
    def insertMenuData(self):
        if (len(self.newMenus) > 0):
            menuValues = ""
            for menuDict in self.newMenus:
                menuValues += (f'({menuDict["menu_id"]}, "{menuDict["meal_type"]}", '
                               f'"{menuDict["location"]}", "{menuDict["menu_date"]}"), \n')

            menuValues = menuValues[:-3]
            with engine.begin() as con:
                con.execute("INSERT INTO menu "
                            "(menu_id, meal_type, location, menu_date) VALUES "
                            f'{menuValues}')

    # insert data into food_on_menu table
    def insertFoodMenuData(self):
        if (len(self.newFoodMenuCombos) > 0):
            foodMenuValues = ""
            for foodMenuDict in self.newFoodMenuCombos:
                foodMenuValues += (f'({foodMenuDict["menu_id"]}, {foodMenuDict["food_id"]}), \n')

            foodMenuValues = foodMenuValues[:-3]
            with engine.begin() as con:
                con.execute("INSERT INTO food_on_menu "
                            "(menu_id, food_id) VALUES "
                            f'{foodMenuValues}')

    # insert data into allergen table
    def insertAllergenData(self):
        if (len(self.newAllergens) > 0):
            allergenValues = ""
            for allergenDict in self.newAllergens:
                allergenValues += (f'({allergenDict["allergen_id"]}, "{allergenDict["allergen_name"]}"), \n')

            allergenValues = allergenValues[:-3]
            with engine.begin() as con:
                con.execute("INSERT INTO allergen "
                            "(allergen_id, allergen_name) VALUES "
                            f'{allergenValues}')

    # inserts data into food_on_allergen table
    def insertFoodAllergenData(self):
        if (len(self.newFoodAllergenCombos) > 0):
            foodAllergenValues = ""
            for foodAllergenDict in self.newFoodAllergenCombos:
                foodAllergenValues += (f'({foodAllergenDict["food_id"]}, {foodAllergenDict["allergen_id"]}), \n')

            foodAllergenValues = foodAllergenValues[:-3]
            with engine.begin() as con:
                con.execute("INSERT INTO food_on_allergen "
                            "(food_id, allergen_id) VALUES "
                            f'{foodAllergenValues}')

    def insertAllData(self):
        self.insertFoodData()
        self.insertMenuData()
        self.insertFoodMenuData()
        self.insertAllergenData()
        self.insertFoodAllergenData()

    def scrapeAll(self, daysToGet):
        EST = datetime.now(timezone('US/Eastern'))  # EST timezone
        date = EST.strftime("%Y-%m-%d")
        daysGotten = 0
        while(daysGotten < daysToGet):
            for location in self.locations:
                self.getData(location, date)
            EST += dt.timedelta(days=1)  # to increment day by one each time
            date = EST.strftime("%Y-%m-%d")
            daysGotten += 1
        self.insertAllData()


scraper = Scraper()

# scrape any number of days
numDaysToScrape = 7
scraper.scrapeAll(numDaysToScrape)
