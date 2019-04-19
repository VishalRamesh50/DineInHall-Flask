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
        rs = con.execute('select distinct * '
                         'from menu join food_on_menu using (menu_id) '
                         ' join food using (food_id) where menu_date '
                         f"= curdate() and location like '{loc}'")

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
        # if user does not choose any location, shows all by default
        if not(iv or steast or stwest):
            iv = True
            steast = True
            stwest = True
        iv = "location like 'IV'" if iv else False
        steast = "location like 'Steast'" if steast else False
        stwest = "location like 'Stwest'" if stwest else False
        calories = f"calories <= {calories}" if calories is not None else True
        protein = f"protein <= {protein}" if protein is not None else True
        fat = f"total_fat <= {fat}" if fat is not None else True
        carbs = f"total_carbs <= {carbs}" if carbs is not None else True
        curdate = datetime.now(timezone('US/Eastern'))  # EST timezone
        curdate = curdate.strftime("%Y-%m-%d")
        with engine.connect() as con:
            foods = con.execute("select distinct * "
                                f"from menu join food_on_menu using (menu_id) "
                                f"join food using (food_id) "
                                f"left join (select food_id, round(avg(stars), 2) ratings from rating group by food_id) food_ratings "
                                f"using (food_id) where menu_date = '{curdate}' "
                                f"and ({iv} or {steast} or {stwest}) "
                                f"and {calories} and {protein} and {fat} and {carbs} "
                                f"and meal_type like '{meal}' "
                                f"and {foodNameQuery}"
                                f"order by location desc, meal_type asc, calories desc, food_name desc")
        foods = list(foods)
        size = len(foods)
        if size == 0:
            flash('No items matched with your query', 'danger')
        else:
            flash(f'Found {size} matching results!', 'success')
    else:
        foods = []
        flash('Start Searching!', 'success')
    return render_template('advancedSearch.html', title='Advanced Search', form=form, allFoods=foods)
