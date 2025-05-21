from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Contraseña actual', validators=[DataRequired()])
    new_password     = PasswordField('Nueva contraseña', validators=[
        DataRequired(),
        EqualTo('confirm', message='Las contraseñas deben coincidir')
    ])
    confirm          = PasswordField('Repetir contraseña')
    submit           = SubmitField('Cambiar contraseña')
