from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, IntegerField, SubmitField, SelectField, DecimalField
from wtforms.validators import Optional, NumberRange


# form to search for food items on advanced search page
class SearchForm(FlaskForm):
    iv = BooleanField('International Village')
    steast = BooleanField('Stetson East')
    stwest = BooleanField('Stetson West')
    meal = SelectField('Meal', choices=[('breakfast', 'Breakfast'), ('lunch', 'Lunch'), ('dinner', 'Dinner')])
    foodName = StringField('Food Name', validators=[Optional()])
    calories = IntegerField('Calories', validators=[Optional(), NumberRange(min=0)])
    protein = IntegerField('Protein', validators=[Optional(), NumberRange(min=0)])
    fat = IntegerField('Fat', validators=[Optional(), NumberRange(min=0)])
    carbs = IntegerField('Carbs', validators=[Optional(), NumberRange(min=0)])
    rating = DecimalField('Rating', validators=[Optional(), NumberRange(min=1, max=5)])
    submit = SubmitField('Search')
