from flask import render_template, request, Blueprint, redirect, url_for, flash
from sqlalchemy.sql import text
from sqlalchemy import create_engine
from datetime import datetime
from pytz import timezone
import os
try:
    SQLALCHEMY_DATABASE_URI = os.environ["SQLALCHEMY_DATABASE_URI"]  # TOKEN from Heroku
except Exception:    
    from ..creds import SQLALCHEMY_DATABASE_URI  # local TOKEN
from .forms import SearchForm

main = Blueprint('main', __name__)

engine = create_engine(SQLALCHEMY_DATABASE_URI)

@main.route("/")
def mainPage():
    return render_template('main.html')


@main.route("/menu")
def home():
    return redirect(url_for('main.filteredLocations', loc='IV'))

@main.route("/menu/<loc>")
def filteredLocations(loc):
    with engine.connect() as con:
        rs = con.execute('select distinct food_name, calories, protein, total_fat, total_carbs, meal_type '
            + 'from menu join food_on_menu using (menu_id) '
            + ' join food using (food_id) where menu_date '
            + "= curdate() and location like '{}'".format(loc))

    foods = list(rs)
    empty = len(foods) == 0
    locations = {'Stwest': False, 'IV': False, 'Steast': False}
    locations[loc] = True

    return render_template('menu.html', allFoods=foods, stwest=locations['Stwest'], iv=locations['IV'], steast=locations['Steast'], empty=empty, title=loc)

@main.route("/AdvancedSearch", methods=['GET', 'POST'])
def search():
    form = SearchForm()
    if form.validate_on_submit():
        iv = form.iv.data
        steast = form.steast.data
        stwest = form.stwest.data
        calories = form.calories.data
        protein = form.protein.data
        fat = form.fat.data
        carbs = form.carbs.data
        meal = form.meal.data
        foodName = form.foodName.data.split()
        foodNameQuery = "true "
        for word in foodName:
            foodNameQuery += f"and food_name like '%%{word}%%' "

        iv = "location like 'IV'" if iv else False
        steast = "location like 'Steast'" if steast else False
        stwest = "location like 'Stwest'" if stwest else False
        calories = "calories <= {}".format(calories) if calories != None else True
        protein = "protein <= {}".format(protein) if protein != None else True
        fat = "total_fat <= {}".format(fat) if fat != None else True
        carbs = "total_carbs <= {}".format(carbs) if carbs != None else True
        curdate = datetime.now(timezone('US/Eastern'))  # EST timezone
        curdate = curdate.strftime("%Y-%m-%d")
        with engine.connect() as con:
            foods = con.execute('select distinct * '
                + "from menu join food_on_menu using (menu_id) "
                + "join food using (food_id) where menu_date = '{}' ".format(curdate)
                + "and ({} or {} or {}) ".format(iv, steast, stwest)
                + "and {} and {} and {} and {} ".format(calories, protein, fat, carbs)
                + "and meal_type like '{}' ".format(meal)
                + "and {}".format(foodNameQuery)
                + "order by location desc, meal_type asc, calories desc")
        foods = list(foods)
        size = len(foods)
        if size==0:
            flash('No items matched with your query', 'danger')
        else:
            flash(f'Found {size} matching results!', 'success')
    else:
        foods = []
        flash('Start Searching!', 'success')
    return render_template('advancedSearch.html', title='Advanced Search', form=form, allFoods=foods)