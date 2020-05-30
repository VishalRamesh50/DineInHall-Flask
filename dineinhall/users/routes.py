from flask import render_template, url_for, flash, redirect, request, Blueprint
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import create_engine

from dineinhall import db, bcrypt
from dineinhall.config import Config
from dineinhall.models import User
from dineinhall.users.forms import (RegistrationForm, LoginForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm)
from dineinhall.users.utils import save_picture, send_reset_email

users = Blueprint('users', __name__)

# allows us to recreate SQL query statements in Python
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)


# register page where the new users can register for an account given the right validated credentials
@users.route("/register", methods=['GET', 'POST'])
def register():
    # if user is already logged in redirect user to home page
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    # user registration form object
    form = RegistrationForm()
    # checks if the user put in valid informaton to register for an account
    if form.validate_on_submit():
        # hashes password to store in database
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        # get user object
        user = User(user_name=form.username.data, email=form.email.data, password=hashed_password)
        # add user to database
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('users.login'))
    return render_template('register.html', title='Register', form=form)


# login page where returning users can log back into their account
@users.route("/login", methods=['GET', 'POST'])
def login():
    # if user is already logged in redirect user to home page
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    # user login form object
    form = LoginForm()
    # checks if the user put in valid informaton to log into their account
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # checks if decrypted password matches the password stored for the user in the database
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            # redirect user to the page they were previously on else redirect to the home page
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


# allows users to log out of their account, if already logged in
@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.home'))


# allows users to see their personal account page with profile picture (must be logged in)
# users can also change their username and email on their account page
@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    # user update account form object
    form = UpdateAccountForm()
    # checks if the user put in valid informaton to update into their account
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.profile_pic = picture_file
        current_user.user_name = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.user_name
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/default.jpg')
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


# shows all reviews/ratings for the specified user
@users.route("/user/<string:username>")
def user_reviews(username):
    with engine.connect() as con:
        # filters out the review from just the given username
        # and a description exists
        reviews = con.execute("select * "
                              f"from food join rating using (food_id) "
                              f"join user using (user_id) "
                              f"where not isnull(description) and user_name='{username}' "
                              f"order by timestamp desc")
    reviews = list(reviews)
    size = len(reviews)

    # determining message displayed after a search
    if size == 0:
        flash('No reviews from this user', 'danger')
    else:
        flash(f'Found {size} reviews!', 'success')
    return render_template('reviews.html', title='Ratings', reviews=reviews)


# allows users to request a password reset
@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    # if user is already logged in redirect user to home page
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    # user request password reset form object
    form = RequestResetForm()
    # checks if the user entered in a valid existing email that's linked to an account to reset their password
    if form.validate_on_submit():
        # get user object
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


# allows users to reset their password
@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    # if user is already logged in redirect user to home page
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    # if there is not a user with the given token
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_request'))
    # user reset password form object
    form = ResetPasswordForm()
    # if the form has been submitted succesfully
    if form.validate_on_submit():
        # hash the users password to store in database
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
