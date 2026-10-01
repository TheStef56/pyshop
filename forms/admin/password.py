from flask_wtf import FlaskForm
from wtforms.validators import Length, EqualTo, Optional
from wtforms import PasswordField

class PassForm(FlaskForm):
    old_password = PasswordField('Vecchia Password', validators=[
        Optional(), Length(min=6)
    ])

    new_password = PasswordField('Nuova Password', validators=[
        Optional(), Length(min=6)
    ])
    confirm_password = PasswordField('Conferma Password', validators=[
        Optional(), EqualTo('new_password', message='Le password devono coincidere.')
    ])

