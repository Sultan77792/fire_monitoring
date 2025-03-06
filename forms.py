from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DecimalField, TextAreaField, FileField, SubmitField, DateField,  SelectField, IntegerField,BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError
from datetime import datetime
from regions import REGIONS_AND_LOCATIONS
def validate_date(form, field):
    if not field.data:
        raise ValidationError('This field is required.')
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Войти')
REGIONS = [
        ('Акмолинская область', 'Акмолинская область'), 
        ('Атырауская область','Атырауская область'),
        ('Алматинская область','Алматинская область'),
        ('Актюбинская область','Актюбинская область'),
        ('Восточно-Казахстанская область','Восточно-Казахстанская область'),
        ('Жамбылская область', 'Жамбылская область'),
        ('Западно-Казахстанская область','Западно-Казахстанская область'),
        ('Карагандинская область','Карагандинская область'),
        ('Костанайская область','Костанайская область'),
        ('Кызылординская область','Кызылординская область'),
        ('Мангыстауская  область','Мангыстауская  область'),
        ('Павлодарская область','Павлодарская область'),
        ('Северо-Казахстанская область','Северо-Казахстанская область'),
        ('Туркестанская область','Туркестанская область'),
        ('Область Абай','Область Абай'),
        ('Область Жетысу','Область Жетысу'),
        ('Область Улытау','Область Улытау'),
        ('г. Астана','г. Астана'),
        ('г. Алматы','г. Алматы'),
        ('г. Шымкент','г. Шымкент'), 
     
]
class FireForm(FlaskForm):
    date = DateField('Date', format='%Y-%m-%d',default=datetime.now, validators=[DataRequired(message='Дата обязательна.'), validate_date])
    region = SelectField('Регион',  choices=[], validators=[DataRequired()])
    location = SelectField('Территория', choices=[], validators=[DataRequired()])
    branch = StringField('Филиал', validators=[Optional()])
    forestry = StringField('Лесничество', validators=[Optional()])
    quarter = StringField('Квартал', validators=[Optional()])
    allotment = StringField('Выдел', validators=[Optional()])
    damage_area = DecimalField('Damage_area', places=4, validators=[DataRequired()])
    damage_les = DecimalField('Damage_les', places=4, validators=[Optional()])
    damage_les_lesopokryt = DecimalField('Damage_les_lesopokryt', places=4, validators=[Optional()])
    damage_les_verh = DecimalField('Damage_les_verh', places=4, validators=[Optional()])
    damage_not_les = DecimalField('Damage_not_les', places=4, validators=[Optional()])
    #  поля лес охрана
    LO_flag = BooleanField('Лесная охрана задействована', validators=[Optional()])
    LO_people_count = IntegerField('Лесная охрана - количество людей', validators=[Optional()])
    LO_tecnic_count = IntegerField('Лесная охрана - количество техники', validators=[Optional()])

    #  поля APS
    APS_flag = BooleanField('АПС задействовано', validators=[Optional()])
    APS_people_count = IntegerField('АПС - количество людей', validators=[Optional()])
    APS_tecnic_count = IntegerField('АПС - количество техники', validators=[Optional()])
    APS_aircraft_count = IntegerField('АПС - количество воздушных судов', validators=[Optional()])

    #  поля KPS
    KPS_flag = BooleanField('МЧС задействовано', validators=[Optional()])
    KPS_people_count = IntegerField('МЧС - количество людей', validators=[Optional()])
    KPS_tecnic_count = IntegerField('МЧС - количество техники', validators=[Optional()])
    KPS_aircraft_count = IntegerField('МЧС - количество воздушных судов', validators=[Optional()])

    #  поля MIO
    MIO_flag = BooleanField('МИО задействовано', validators=[Optional()])
    MIO_people_count = IntegerField('МИО - количество людей', validators=[Optional()])
    MIO_tecnic_count = IntegerField('МИО - количество техники', validators=[Optional()])
    MIO_aircraft_count = IntegerField('МИО - количество воздушных судов', validators=[Optional()])

    #  поля других организаций
    other_org_flag = BooleanField('Другие организации задействованы', validators=[Optional()])
    other_org_people_count = IntegerField('Другие организации - количество людей', validators=[Optional()])
    other_org_tecnic_count = IntegerField('Другие организации - количество техники',validators=[Optional()])
    other_org_aircraft_count = IntegerField('Другие организации - количество воздушных судов', validators=[Optional()])

    description = TextAreaField('Description', validators=[Optional()])
    damage_tenge = IntegerField('Ущерб (тенге)', validators=[Optional()])
    firefighting_costs = IntegerField('Затраты на тушение', validators=[Optional()])
    KPO = IntegerField('КПО',validators=[Optional()])
    file = FileField('Attach a file', validators=[Optional()])
    submit = SubmitField('Сохранить')

class ExportForm(FlaskForm):
    start_date = DateField('Start Date', format='%Y-%m-%d')
    end_date = DateField('End Date', format='%Y-%m-%d')
    submit = SubmitField('Export')
