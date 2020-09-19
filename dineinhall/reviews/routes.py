from datetime import datetime
from flask import render_template, Blueprint, redirect, url_for, flash
from flask_login import current_user, login_required
from pytz import timezone
from sqlalchemy import create_engine

from .forms import ReviewForm
from dineinhall import db
from dineinhall.config import Config
from dineinhall.models import Rating

review = Blueprint('review', __name__)

# allows us to recreate SQL query statements in Python
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)


# page where user creates a new review (must be logged in)
@review.route("/newReview/<food_id>", methods=['GET', 'POST'])
@login_required
def newReview(food_id):
    # food review form object
    form = ReviewForm()
    if form.validate_on_submit():
        user_id = current_user.user_id
        stars = form.stars.data
        description = form.description.data.strip()
        # description is None type if not input
        description = description if description else None
        timestamp = datetime.now(timezone('US/Eastern'))  # EST timezone
        timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        rating = Rating(user_id=user_id, food_id=food_id, stars=stars, description=description, timestamp=timestamp)
        try:
            db.session.add(rating)
            db.session.commit()
            flash('Succesfully reviewed', 'success')
        except Exception:
            flash('Error in submitting review', 'danger')
    return render_template('newRating.html', title='New Review', form=form)


# displays the reviews and rating for every food that has been reviewed/rated
@review.route("/reviews")
def reviews():
    return redirect(url_for('review.foodReview', food_id=-1))


# displays the reviews and rating for the specified food
@review.route("/reviews/<food_id>")
def foodReview(food_id):
    if int(food_id) == -1:
        food_id = True
    else:
        food_id = f'food_id = {food_id}'
    with engine.connect() as con:
        # all the reviews for the given food id where the description exists
        reviews = con.execute("select * "
                              f"from food join rating using (food_id) "
                              f"join user using (user_id) "
                              f"where not isnull(rating.description) and {food_id} "
                              f"order by timestamp desc")
    reviews = list(reviews)
    size = len(reviews)

    # if there are no reviews for the given food id
    if size == 0:
        flash('No reviews found', 'danger')
    else:
        flash(f'Found {size} reviews!', 'success')
    return render_template('reviews.html', title='Ratings', reviews=reviews)
