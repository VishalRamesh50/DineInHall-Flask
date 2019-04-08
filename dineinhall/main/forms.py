from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, IntegerField, SubmitField, SelectField
from wtforms.validators import Optional, NumberRange

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
	submit = SubmitField('Search')