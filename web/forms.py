from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from web.models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class SignupForm(FlaskForm):
    first_name = StringField('First Name', 
                           validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', 
                          validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', 
                       validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                           validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                   validators=[DataRequired(), EqualTo('password')])
    terms = BooleanField('I agree to the Terms of Service', 
                        validators=[DataRequired()])
    submit = SubmitField('Create Account')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email address already exists. Please choose a different one.')

class FeedbackForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Feedback', validators=[DataRequired()])
    rating = SelectField('Rating', 
                        choices=[('5', '5 Stars - Excellent'), 
                                ('4', '4 Stars - Good'), 
                                ('3', '3 Stars - Average'), 
                                ('2', '2 Stars - Poor'), 
                                ('1', '1 Star - Terrible')],
                        validators=[DataRequired()])
    submit = SubmitField('Submit Feedback')

class PublicFeedbackForm(FlaskForm):
    customer_name = StringField('Your Name (Optional)', validators=[Optional(), Length(max=100)])
    customer_email = StringField('Your Email (Optional)', validators=[Optional(), Email()])
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Your Feedback', validators=[DataRequired(), Length(max=1000)], 
                          render_kw={"placeholder": "Tell us about your experience..."})
    rating = SelectField('How would you rate your experience?', 
                        choices=[('5', '⭐⭐⭐⭐⭐ Excellent'), 
                                ('4', '⭐⭐⭐⭐ Good'), 
                                ('3', '⭐⭐⭐ Average'), 
                                ('2', '⭐⭐ Poor'), 
                                ('1', '⭐ Terrible')],
                        validators=[DataRequired()])
    submit = SubmitField('Submit Feedback')