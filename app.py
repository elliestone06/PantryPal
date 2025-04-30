from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
import requests
import json
import os
import email_validator
from datetime import datetime
from collections import defaultdict
import Recipe as recipe
"""This file acts as the backend for our web page, handling things like loading items, generating recipes, creating an account, logging
in and out, saving all the user input data, and the organization of the grocery items they enter."""

"""This starts the Flask app and sets up the base line for the account system."""
app = Flask(__name__)
app.config['SECRET_KEY'] = 'peanut_goober'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! Return to the log in page.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route("/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            print(f"User found: {user.email}")
        else:
            print("User not found.")
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Your credentials are either incorrect or not found. Please try agian.', 'danger')
    return render_template('login.html', form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))
""" This function runs when a user selects to log out, and it takes them to a new page where they can either close the
    application or locate the option choose to log in again."""

data_file = 'data.json'
def load_items():
    """
    This loads the items from the json file. If it is empty it shows nothing, otherwise it shows the contents. New accounts start with an empty list.
    """
    if os.path.exists(data_file):
        with open(data_file, 'r') as file:
            return json.load(file)
    return []

def save_items():
    """
    Literally just uploads the item to the json file to be saved, as you delete or add items it will automatically update. I like that .dump is 
    the right feature to use.
    """
    with open(data_file, 'w') as file:
        json.dump(items, file, indent=4)

"""This loads items when the app runs."""
items = load_items()

@app.route("/index")
@login_required
def index():
    """
    Items in the same category will be grouped together, and dislay the expiration date that is closest to expiring first.
    """
    """This creats the structure for the dictionary."""
    categorized = defaultdict(lambda: defaultdict(list))

    """This is a simple for loop that gathers and separates the user input data for each item, preparing it for how it will be formatted in the index."""
    for i, item in enumerate(items):
        category = item.get("category", "Unknown")
        name = item.get("name", "Unnamed")
        expiration = item.get("expiration", "")
        categorized[category][name].append({"expiration": expiration, "index": i})

   """This makes it so that within every category, the one with the soonest expiration date will appear at the top of the list. Shoutout to classmates for
   suggesting this."""
    def safe_parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return datetime.max
    for category in categorized:
        for name in categorized[category]:
            categorized[category][name].sort(
                key=lambda entry: safe_parse_date(entry["expiration"])
    )
   """This takes the things we just categorized and sorts them alphabetically. There isn't really a reason for this, we just thought it was cool to have extra 
   organization."""
    sorted_categorized = dict(sorted(categorized.items()))

    return render_template("index.html", categorized_items=sorted_categorized)

@app.route("/add", methods=["POST"])
@login_required
def add_item():
    """
    This adds the entered item to the inventory using its expiration, category, and name data.
    """
    name = request.form.get("item", "").strip().title()
    category = request.form.get("category", "").strip().title()
    expiration = request.form.get("expiration", "").strip()

    items.append({"name": name, "category": category, "expiration": expiration})
    save_items()

    return redirect(url_for("index"))

@app.route("/remove/<int:item_index>")
@login_required
def remove_item(item_index):
    """
    This removes the chosen item from the inventory using the pop function.
    """
    if 0 <= item_index < len(items):
        items.pop(item_index)
        save_items()

    return redirect(url_for("index"))

@app.route("/lookup")
def barcode_lookup():
    """
    This looks up a product if its barcode is stored in the API.
    """
    barcode = request.args.get("barcode")
    if not barcode:
        return jsonify({}), 400

    try:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url)
        data = response.json()

        if data.get("status") != 1:
            return jsonify({}), 404

        product = data.get("product", {})
        name = product.get("product_name", "")
        category = product.get("categories_tags", [""])[0].replace("en:", "").title() if product.get("categories_tags") else ""

        return jsonify({
            "name": name,
            "category": category,
            "expiration": ""
        })
    except Exception as e:
        print("Open Food Facts API error:", e)
        return jsonify({}), 500
    
@app.route("/recipe")
def makeRecipe():
    title, ingredients, directions = recipe.make()
    return jsonify({
        "title": title,
        "ingredients": ingredients,
        "directions" : directions
    })

@app.route("/account")
@login_required
def account():
    return render_template("account.html", user=current_user)

if __name__ == "__main__":
    # Run the app in debug mode for development/testing
    app.run(debug=True)
