from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange, Length


class ReviewForm(FlaskForm):
    stars = IntegerField('Stars', validators=[DataRequired(), NumberRange(min=1, max=5)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=300)])
    submit = SubmitField('Submit')
