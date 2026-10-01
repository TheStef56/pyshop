from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, URL
from wtforms import StringField, EmailField, TelField, TextAreaField, SelectField, IntegerField, FileField

class SettingsForm(FlaskForm):
    site_name = StringField('Nome sito', validators=[DataRequired()])
    site_description = StringField('Descrizione sito', validators=[Optional()])
    support_mail = StringField('Email di supporto', validators=[DataRequired(), Email()])
    
    tiktok_profile_url = StringField('Profilo TikTok', validators=[Optional(), URL()])
    instagram_profile_url = StringField('Profilo Instagram', validators=[Optional(), URL()])
    youtube_profile_url = StringField('Profilo YouTube', validators=[Optional(), URL()])

    contact_whatsapp = StringField('Whatsapp', validators=[Optional()])
    contact_phone = StringField('Telefono', validators=[Optional()])
    contact_instagram = StringField('Instagram', validators=[Optional()])
    contact_facebook = StringField('Facebook', validators=[Optional()])
    contact_mail = StringField('Mail', validators=[Optional(), Email()])

    open = SelectField('Stato del negozio', choices=[('open', 'Aperto'), ('closed', 'Chiuso')], default='open', validators=[DataRequired()])
    processing_time = IntegerField('Tempo di lavorazione prodotti', default=3, validators=[DataRequired(), NumberRange(1, 9999)])
    
    header_image = FileField('Immagine Header', validators=[Optional()])
    logo_image = FileField('Logo', validators=[Optional()])
    favicon_image = FileField('Favicon (512x512 is recommended)', validators=[Optional()])
    homepage_en_image = FileField('Homepage ENG', validators=[Optional()])
    homepage_it_image = FileField('Homepage IT', validators=[Optional()])

    privacy_policy_en = TextAreaField('Privacy policy (en)', validators=[DataRequired()])
    privacy_policy_it = TextAreaField('Privacy policy (it)', validators=[DataRequired()])
