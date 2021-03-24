from flask.app import Flask
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length


class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField('text', validators=[DataRequired()])


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])
    image_url = StringField('(Optional) Image URL')


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])


class UserDetailForm(FlaskForm):
    """form to add details to a user's profile"""

    bio = StringField('Bio',validators=[Length(max=140)])
    loc = StringField('(Optional) Location')
    backimg = StringField('(Optional) Background Image URL')
    pfp = StringField('(Optional) Profile Image URL')
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    new_username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])


