from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Optional, URL
from wtforms import StringField, SelectField, TextAreaField, FileField

class LabelForm(FlaskForm):
    name = StringField('Nome marca', validators=[DataRequired()])
    image = FileField('Logo marca', validators=[Optional()])