from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, Regexp
from web.models import User, Shopkeeper
import re

class CustomValidators:
    """Custom validation methods for forms"""
    
    @staticmethod
    def validate_name(form, field):
        """Validate name fields - only letters, spaces, hyphens, apostrophes"""
        if not re.match(r"^[a-zA-Z\s\-']+$", field.data):
            raise ValidationError('Name can only contain letters, spaces, hyphens, and apostrophes.')
    
    @staticmethod
    def validate_username(form, field):
        """Validate username format - alphanumeric and underscores only"""
        if not re.match(r'^[a-zA-Z0-9_]+$', field.data):
            raise ValidationError('Username can only contain letters, numbers, and underscores.')
    
    @staticmethod
    def validate_shop_name(form, field):
        """Validate shop name - allow letters, numbers, spaces, and common punctuation"""
        if not re.match(r"^[a-zA-Z0-9\s\-'&.,()]+$", field.data):
            raise ValidationError('Shop name contains invalid characters.')
    
    @staticmethod
    def validate_password_strength(form, field):
        """Validate password strength"""
        password = field.data
        errors = []
        
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter.')
        
        if not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter.')
        
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one number.')
        
        if errors:
            raise ValidationError(' '.join(errors))
    
    @staticmethod
    def validate_rating(form, field):
        """Validate rating is between 1 and 5"""
        try:
            rating = int(field.data)
            if not (1 <= rating <= 5):
                raise ValidationError('Rating must be between 1 and 5 stars.')
        except (ValueError, TypeError):
            raise ValidationError('Rating must be a valid number between 1 and 5.')
    
    @staticmethod
    def validate_content_length(min_length=10, max_length=1000):
        """Factory function to create content length validator"""
        def _validate_content_length(form, field):
            content = field.data.strip() if field.data else ''
            if len(content) < min_length:
                raise ValidationError(f'Content must be at least {min_length} characters long.')
            if len(content) > max_length:
                raise ValidationError(f'Content cannot exceed {max_length} characters.')
        return _validate_content_length

class LoginForm(FlaskForm):
    """User login form"""
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email is required.'),
            Email(message='Please enter a valid email address.')
        ],
        render_kw={
            'placeholder': 'Enter your email address',
            'class': 'form-control',
            'autocomplete': 'email'
        }
    )
    
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.')
        ],
        render_kw={
            'placeholder': 'Enter your password',
            'class': 'form-control',
            'autocomplete': 'current-password'
        }
    )
    
    submit = SubmitField(
        'Login',
        render_kw={'class': 'btn btn-primary btn-block'}
    )

class SignupForm(FlaskForm):
    """Customer signup form"""
    first_name = StringField(
        'First Name',
        validators=[
            DataRequired(message='First name is required.'),
            Length(min=2, max=50, message='First name must be between 2 and 50 characters.'),
            CustomValidators.validate_name
        ],
        render_kw={
            'placeholder': 'Enter your first name',
            'class': 'form-control',
            'autocomplete': 'given-name'
        }
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            DataRequired(message='Last name is required.'),
            Length(min=2, max=50, message='Last name must be between 2 and 50 characters.'),
            CustomValidators.validate_name
        ],
        render_kw={
            'placeholder': 'Enter your last name',
            'class': 'form-control',
            'autocomplete': 'family-name'
        }
    )
    
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email is required.'),
            Email(message='Please enter a valid email address.')
        ],
        render_kw={
            'placeholder': 'Enter your email address',
            'class': 'form-control',
            'autocomplete': 'email'
        }
    )
    
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.'),
            Length(min=8, message='Password must be at least 8 characters long.'),
            CustomValidators.validate_password_strength
        ],
        render_kw={
            'placeholder': 'Create a strong password',
            'class': 'form-control',
            'autocomplete': 'new-password'
        }
    )
    
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password.'),
            EqualTo('password', message='Passwords must match.')
        ],
        render_kw={
            'placeholder': 'Confirm your password',
            'class': 'form-control',
            'autocomplete': 'new-password'
        }
    )

    submit = SubmitField(
        'Create Account',
        render_kw={'class': 'btn btn-success btn-block'}
    )
    
    def validate_email(self, email):
        """Check if email already exists"""
        # Strip whitespace and convert to lowercase
        email_clean = email.data.strip().lower()
        user = User.query.filter(User.email.ilike(email_clean)).first()
        if user:
            raise ValidationError('This email address is already registered. Please use a different email.')


class ShopkeeperSignupForm(FlaskForm):
    """Shopkeeper signup form"""
    first_name = StringField(
        'First Name',
        validators=[
            DataRequired(message='First name is required.'),
            Length(min=2, max=50, message='First name must be between 2 and 50 characters.'),
            CustomValidators.validate_name
        ],
        render_kw={
            'placeholder': 'Enter your first name',
            'class': 'form-control',
            'autocomplete': 'given-name'
        }
    )
    
    last_name = StringField(
        'Last Name',
        validators=[
            DataRequired(message='Last name is required.'),
            Length(min=2, max=50, message='Last name must be between 2 and 50 characters.'),
            CustomValidators.validate_name
        ],
        render_kw={
            'placeholder': 'Enter your last name',
            'class': 'form-control',
            'autocomplete': 'family-name'
        }
    )
    
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(message='Email is required.'),
            Email(message='Please enter a valid email address.')
        ],
        render_kw={
            'placeholder': 'Enter your business email',
            'class': 'form-control',
            'autocomplete': 'email'
        }
    )
    
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.'),
            Length(min=8, message='Password must be at least 8 characters long.'),
            CustomValidators.validate_password_strength
        ],
        render_kw={
            'placeholder': 'Create a strong password',
            'class': 'form-control',
            'autocomplete': 'new-password'
        }
    )
    
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password.'),
            EqualTo('password', message='Passwords must match.')
        ],
        render_kw={
            'placeholder': 'Confirm your password',
            'class': 'form-control',
            'autocomplete': 'new-password'
        }
    )
    
    shop_name = StringField(
        'Shop Name',
        validators=[
            DataRequired(message='Shop name is required.'),
            Length(min=2, max=100, message='Shop name must be between 2 and 100 characters.'),
            CustomValidators.validate_shop_name
        ],
        render_kw={
            'placeholder': 'Enter your shop name',
            'class': 'form-control',
            'autocomplete': 'organization'
        }
    )
    
    username = StringField(
        'Shop Username',
        validators=[
            DataRequired(message='Username is required.'),
            Length(min=3, max=50, message='Username must be between 3 and 50 characters.'),
            CustomValidators.validate_username
        ],
        render_kw={
            'placeholder': 'Choose a unique username',
            'class': 'form-control',
            'autocomplete': 'username'
        }
    )

    submit = SubmitField(
        'Create Shop Account',
        render_kw={'class': 'btn btn-success btn-block'}
    )
    
    def validate_username(self, username):
        """Check if username already exists"""
        # Strip whitespace and convert to lowercase
        username_clean = username.data.strip().lower()
        shopkeeper = Shopkeeper.query.filter(Shopkeeper.username.ilike(username_clean)).first()
        if shopkeeper:
            raise ValidationError('This username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        """Check if email already exists"""
        # Strip whitespace and convert to lowercase
        email_clean = email.data.strip().lower()
        user = User.query.filter(User.email.ilike(email_clean)).first()
        if user:
            raise ValidationError('This email address is already registered. Please use a different email.')


class FeedbackForm(FlaskForm):
    """Feedback form for logged-in users"""
    title = StringField(
        'Feedback Title',
        validators=[
            DataRequired(message='Title is required.'),
            Length(min=3, max=100, message='Title must be between 3 and 100 characters.'),
        ],
        render_kw={
            'placeholder': 'Brief summary of your feedback',
            'class': 'form-control'
        }
    )
    
    content = TextAreaField(
        'Your Feedback',
        validators=[
            DataRequired(message='Feedback content is required.'),
            CustomValidators.validate_content_length(min_length=10, max_length=1000),
        ],
        render_kw={
            'placeholder': 'Share your detailed feedback here...',
            'class': 'form-control',
            'rows': 4
        }
    )
    
    rating = SelectField(
        'Overall Rating',
        choices=[
            ('5', '⭐⭐⭐⭐⭐ Excellent (5 stars)'),
            ('4', '⭐⭐⭐⭐ Good (4 stars)'),
            ('3', '⭐⭐⭐ Average (3 stars)'),
            ('2', '⭐⭐ Poor (2 stars)'),
            ('1', '⭐ Terrible (1 star)')
        ],
        validators=[
            DataRequired(message='Please select a rating.'),
            CustomValidators.validate_rating
        ],
        render_kw={'class': 'form-select'}
    )
    
    submit = SubmitField(
        'Submit Feedback',
        render_kw={'class': 'btn btn-primary'}
    )


class PublicFeedbackForm(FlaskForm):
    """Public feedback form for non-logged-in users"""
    customer_name = StringField(
        'Your Name',
        validators=[
            Optional(),
            Length(max=100, message='Name cannot exceed 100 characters.'),
            CustomValidators.validate_name
        ],
        render_kw={
            'placeholder': 'Enter your name',
            'class': 'form-control'
        }
    )
    
    customer_email = StringField(
        'Your Email (Optional)',
        validators=[
            Optional(),
            Email(message='Please enter a valid email address.')
        ],
        render_kw={
            'placeholder': 'Enter your email (optional)',
            'class': 'form-control',
            'autocomplete': 'email'
        }
    )
    
    title = StringField(
        'Feedback Title',
        validators=[
            DataRequired(message='Title is required.'),
            Length(min=3, max=100, message='Title must be between 3 and 100 characters.'),
        ],
        render_kw={
            'placeholder': 'Brief summary of your experience',
            'class': 'form-control'
        }
    )
    
    content = TextAreaField(
        'Your Feedback',
        validators=[
            DataRequired(message='Feedback content is required.'),
            CustomValidators.validate_content_length(min_length=10, max_length=1000),
        ],
        render_kw={
            'placeholder': 'Tell us about your experience with this shop...',
            'class': 'form-control',
            'rows': 4
        }
    )
    
    rating = SelectField(
        'How would you rate your experience?',
        choices=[
            ('5', '⭐⭐⭐⭐⭐ Excellent'),
            ('4', '⭐⭐⭐⭐ Good'),
            ('3', '⭐⭐⭐ Average'),
            ('2', '⭐⭐ Poor'),
            ('1', '⭐ Terrible')
        ],
        validators=[
            DataRequired(message='Please select a rating.'),
            CustomValidators.validate_rating
        ],
        render_kw={'class': 'form-select'}
    )

    submit = SubmitField(
        'Submit Feedback',
        render_kw={'class': 'btn btn-success btn-lg'}
    )
    
    def validate_customer_name(self, customer_name):
        """Validate customer name if provided"""
        if customer_name.data:
            # Strip whitespace
            customer_name.data = customer_name.data.strip()
            if len(customer_name.data) < 2:
                raise ValidationError('Name must be at least 2 characters long.')
    
    def validate_customer_email(self, customer_email):
        """Validate customer email if provided"""
        if customer_email.data:
            # Strip whitespace and convert to lowercase
            customer_email.data = customer_email.data.strip().lower()


class FeedbackFilterForm(FlaskForm):
    """Form for filtering feedback"""
    rating = SelectField(
        'Filter by Rating',
        choices=[
            ('', 'All Ratings'),
            ('5', '⭐⭐⭐⭐⭐ (5 stars)'),
            ('4', '⭐⭐⭐⭐ (4 stars)'),
            ('3', '⭐⭐⭐ (3 stars)'),
            ('2', '⭐⭐ (2 stars)'),
            ('1', '⭐ (1 star)')
        ],
        validators=[
            Optional(),
            CustomValidators.validate_rating
        ],
        render_kw={'class': 'form-select'}
    )

    date_range = SelectField(
        'Filter by Date',
        choices=[
            ('', 'All Time'),
            ('7', 'Last 7 days'),
            ('30', 'Last 30 days'),
            ('90', 'Last 90 days')
        ],
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )
    
    submit = SubmitField(
        'Apply Filters',
        render_kw={'class': 'btn btn-outline-primary'}
    )