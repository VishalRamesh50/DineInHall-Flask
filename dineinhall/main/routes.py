from flask import render_template, Blueprint, redirect, url_for, flash
from sqlalchemy import create_engine
from datetime import datetime
from pytz import timezone
from .forms import SearchForm
import os
try:
    SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]  # URI from Heroku
except Exception:
    from ..creds import SQLALCHEMY_DATABASE_URI  # local URI

main = Blueprint('main', __name__)

# allows us to recreate SQL query statements in Python
engine = create_engine(SQLALCHEMY_DATABASE_URI)


# routes the user to the home page
@main.route("/")
def mainPage():
    return render_template('main.html')


# routes the user to the menu page with the default location being IV
@main.route("/menu")
def home():
    return redirect(url_for('main.filteredLocations', loc='IV'))


# routes the user to the menu page with the given location tag
@main.route("/menu/<loc>")
def filteredLocations(loc):
    with engine.connect() as con:
        # find all the foods for the current date from the given location
        rs = con.execute('select distinct * '
                         'from menu join food_on_menu using (menu_id) '
                         ' join food using (food_id) where menu_date '
                         f"= curdate() and location like '{loc}'")

    foods = list(rs)
    # if there are foods available that day for the given location
    empty = len(foods) == 0
    locations = {'Stwest': False, 'IV': False, 'Steast': False}
    # sets the used location to be true in order to display location name
    locations[loc] = True

    return render_template('menu.html', allFoods=foods, stwest=locations['Stwest'], iv=locations['IV'], steast=locations['Steast'], empty=empty, title=loc)


# the advanced search page for querying foods using specific attributes
@main.route("/AdvancedSearch", methods=['GET', 'POST'])
def search():
    # search form object
    form = SearchForm()
    if form.validate_on_submit():
        # boolean values for location
        iv = form.iv.data
        steast = form.steast.data
        stwest = form.stwest.data
        # numeric values for nutrients
        calories = form.calories.data
        protein = form.protein.data
        fat = form.fat.data
        carbs = form.carbs.data
        # breakfast, lunch, or dinner
        meal = form.meal.data
        # split food name into a list of strings
        foodName = form.foodName.data.split()
        # rating on a 5pt scale
        rating = form.rating.data
        foodNameQuery = "true "
        # for each word in the searched food find a food item that contains the given word
        for word in foodName:
            foodNameQuery += f"and food_name like '%%{word}%%' "
        # if user does not choose any location, shows all by default
        if not(iv or steast or stwest):
            iv = True
            steast = True
            stwest = True
        # foods from dining hall locations
        iv = "location like 'IV'" if iv else False
        steast = "location like 'Steast'" if steast else False
        stwest = "location like 'Stwest'" if stwest else False
        # foods less or equal to than the given calories
        calories = f"calories <= {calories}" if calories is not None else True
        # foods more than or equal to the given protein
        protein = f"protein >= {protein}" if protein is not None else True
        # foods less than or equal to the given fat
        fat = f"total_fat <= {fat}" if fat is not None else True
        # foods less than or equal to the given carbs
        carbs = f"total_carbs <= {carbs}" if carbs is not None else True
        # foods with ratings above the given rating (including not yet rated)
        rating = f"(ratings >= {rating} or isnull(ratings))" if rating is not None else True
        # set a timezone to avoid the inconsistent timezone of the Heroku server
        curdate = datetime.now(timezone('US/Eastern'))  # EST timezone
        curdate = curdate.strftime("%Y-%m-%d")
        with engine.connect() as con:
            # main query searching for food items with all the specified attributes
            # if a value is not given deafault it to True so the query skips over it
            foods = con.execute("select distinct * "
                                f"from menu join food_on_menu using (menu_id) "
                                f"join food using (food_id) "
                                f"left join (select food_id, round(avg(stars), 2) ratings from rating group by food_id) food_ratings "
                                f"using (food_id) where menu_date = '{curdate}' "
                                f"and ({iv} or {steast} or {stwest}) "
                                f"and {calories} and {protein} and {fat} and {carbs} "
                                f"and meal_type like '{meal}' "
                                f"and {rating} "
                                f"and {foodNameQuery} "
                                f"order by location desc, meal_type asc, calories desc, food_name desc")
        foods = list(foods)
        size = len(foods)
        # if there are no foods for the given specifications
        if size == 0:
            flash('No items matched with your query', 'danger')
        else:
            flash(f'Found {size} matching results!', 'success')
    else:
        foods = []
        # default message which pops up once going to the page
        flash('Start Searching!', 'success')
    return render_template('advancedSearch.html', title='Advanced Search', form=form, allFoods=foods)
