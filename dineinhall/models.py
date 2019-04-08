from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from dineinhall import db, login_manager
from flask_login import UserMixin
import os
try:
    from .creds import SECRET_KEY
except:
    SECRET_KEY = os.environ['SECRET_KEY']

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_pic = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    # posts = db.relationship('Post', backref='author', lazy=True)

    def get_id(self):
        return (self.user_id)

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(SECRET_KEY, expires_sec)
        return s.dumps({'user_id': self.user_id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(SECRET_KEY)
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.user_name}', '{self.email}', '{self.profile_pic}')"


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

class Menu(db.Model):
    menu_id = db.Column(db.Integer, primary_key=True)
    meal_type = db.Column(db.Enum('breakfast', 'lunch', 'dinner'), nullable=False)
    location = db.Column(db.Enum('Stwest', 'Steast', 'IV'), nullable=True)
    menu_date = db.Column(db.DateTime, nullable=True)

class FoodOnMenu(db.Model):
    # compound primary keys
    food_id = db.Column(db.Integer, db.ForeignKey('menu.menu_id'), primary_key=True, nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('food.food_id'), primary_key=True, nullable=False)