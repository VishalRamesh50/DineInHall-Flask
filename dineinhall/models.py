from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from dineinhall import db, login_manager
from flask_login import UserMixin
import os
try:
    from .creds import SECRET_KEY
except Exception:
    SECRET_KEY = os.environ['SECRET_KEY']


# This file is used to create table models for SQLAlchemy.
# It allows for the SQLAlchemy API to interract with the database.

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Model for the user table in the database.
class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_pic = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)

    # get user_id
    def get_id(self):
        return (self.user_id)

    # generate random token which expires in 30 mins
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(SECRET_KEY, expires_sec)
        return s.dumps({'user_id': self.user_id}).decode('utf-8')

    # method to verify the user's reset token
    @staticmethod
    def verify_reset_token(token):
        s = Serializer(SECRET_KEY)
        try:
            user_id = s.loads(token)['user_id']
        except Exception:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.user_name}', '{self.email}', '{self.profile_pic}')"


# Model for the food table in the database.
class Food(db.Model):
    food_id = db.Column(db.Integer, primary_key=True)
    food_name = db.Column(db.String(100), nullable=True)
    serving = db.Column(db.Integer, nullable=True)
    calories = db.Column(db.Integer, nullable=True)
    calories_from_fat = db.Column(db.Integer, nullable=True)
    cholesterol = db.Column(db.Integer, nullable=True)
    dietary_fiber = db.Column(db.Integer, nullable=True)
    protein = db.Column(db.Integer, nullable=True)
    saturated_fat = db.Column(db.Integer, nullable=True)
    sodium = db.Column(db.Integer, nullable=True)
    sugar = db.Column(db.Integer, nullable=True)
    total_carbs = db.Column(db.Integer, nullable=True)
    total_fat = db.Column(db.Integer, nullable=True)
    trans_fat = db.Column(db.Integer, nullable=True)
    vitamin_d = db.Column(db.Integer, nullable=True)
    vegetarian = db.Column(db.Boolean, nullable=False)
    vegan = db.Column(db.Boolean, nullable=False)
    balanced = db.Column(db.Boolean, nullable=False)


# Model for the menu table in the database.
class Menu(db.Model):
    menu_id = db.Column(db.Integer, primary_key=True)
    meal_type = db.Column(db.Enum('breakfast', 'lunch', 'dinner'), nullable=False)
    location = db.Column(db.Enum('Stwest', 'Steast', 'IV'), nullable=True)
    menu_date = db.Column(db.DateTime, nullable=True)


# Model for the food_on_menu table in the database.
class FoodOnMenu(db.Model):
    # compound primary keys
    food_id = db.Column(db.Integer, db.ForeignKey('menu.menu_id'), primary_key=True, nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('food.food_id'), primary_key=True, nullable=False)


# Model for the rating table in the database.
class Rating(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), primary_key=True, nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food.food_id'), primary_key=True, nullable=False)
    stars = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(300), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=True)
