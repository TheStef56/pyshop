from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from wtforms import StringField, PasswordField, BooleanField, EmailField

class UserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), Length(min=3, max=25)
    ])
    password = PasswordField('Password', validators=[
        Optional(), Length(min=6)
    ])
    confirm_password = PasswordField('Conferma Password', validators=[
        Optional(), EqualTo('password', message='Le password devono coincidere.')
    ])
    email = EmailField('Email', validators=[
        DataRequired(), Email()
    ])
    is_active = BooleanField('Attivo')
