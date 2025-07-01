from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from web import db
from web.models import  User ,Shopkeeper 
from web.forms import LoginForm, SignupForm ,ShopkeeperSignupForm
from flask import session



auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    #if current_user.is_authenticated:
     #   if isinstance(current_user, Shopkeeper):
     #       return redirect(url_for('main.dashboard'))
     #   elif isinstance(current_user, User):
     #       return redirect(url_for('customer.dashboard'))

    
    form = LoginForm()
    if form.validate_on_submit():
        # Check if the user is a shopkeeper or a customer
        customer = User.query.filter_by(email=form.email.data).first()
        shopkeeper = Shopkeeper.query.filter_by(email=form.email.data).first()

        if shopkeeper and check_password_hash(shopkeeper.password_hash, form.password.data):
            login_user(shopkeeper, remember=form.remember_me.data)
            session['shopname'] = shopkeeper.shopname   # ✅ Store shopname in session
            flash('Shopkeeper login successful!', 'success')
            return redirect(url_for('main.dashboard'))

        elif customer and check_password_hash(customer.password_hash, form.password.data):
            login_user(customer, remember=form.remember_me.data)
            session.pop('shopname', None)
            flash('Customer login successful!', 'success')
            return redirect(url_for('customer.dashboard'))

        else:
            flash('Invalid email or password', 'error')

    return render_template('auth/login.html', form=form)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = SignupForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email address already exists', 'error')
            return render_template('auth/signup.html', form=form)
        
        # Create new user
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html', form=form)


@auth.route('/signupshop', methods=['GET', 'POST'])
def signupshop():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ShopkeeperSignupForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email address already exists', 'error')
            return render_template('auth/signupshop.html', form=form)
        
        # Create new user
        user = Shopkeeper(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            shopname=form.shopname.data,
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data)
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Shop added successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signupshop.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.homepage'))