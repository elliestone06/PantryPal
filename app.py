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

# Initialize the Flask application
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

# Define the path to the JSON file that will store grocery items
# This serves as a lightweight persistent storage
data_file = 'data.json'
def load_items():
    """
    Load items from the data file (data.json).
    If the file exists, it reads the content and parses the JSON into a Python list.
    If the file doesn't exist, it returns an empty list.

    Returns:
        list: A list of grocery items.
    """
    if os.path.exists(data_file):
        with open(data_file, 'r') as file:
            return json.load(file)
    return []

def save_items():
    """
    Save the current list of grocery items to the data file (data.json).
    Converts the list to JSON format and writes it to the file.
    """
    with open(data_file, 'w') as file:
        json.dump(items, file, indent=4)

# Load items when the application starts
items = load_items()

@app.route("/index")
@login_required
def index():
    """
    Render the main index page, showing all grocery items organized by category and name.
    Items with the same name are grouped together and their expiration dates listed.

    Returns:
        str: Rendered HTML page with categorized grocery data.
    """
    # Dictionary structure: {category: {name: [ {expiration, index}, ... ]}}
    categorized = defaultdict(lambda: defaultdict(list))

    for i, item in enumerate(items):
        category = item.get("category", "Unknown")
        name = item.get("name", "Unnamed")
        expiration = item.get("expiration", "")
        categorized[category][name].append({"expiration": expiration, "index": i})

    # Sort expiration dates for each grouped item
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
    # Sort categories alphabetically for display
    sorted_categorized = dict(sorted(categorized.items()))

    return render_template("index.html", categorized_items=sorted_categorized)

@app.route("/add", methods=["POST"])
@login_required
def add_item():
    """
    Handle the form submission to add a new grocery item.
    Extracts the item name, category, and expiration date from the form data,
    adds it to the item list, and saves the list to the data file.

    Returns:
        Response: Redirects to the index page.
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
    Remove a grocery item based on its index in the list.
    Ensures the index is valid before removing the item and then saves the updated list.

    Args:
        item_index (int): Index of the item to remove.

    Returns:
        Response: Redirects to the index page.
    """
    if 0 <= item_index < len(items):
        items.pop(item_index)
        save_items()

    return redirect(url_for("index"))

@app.route("/lookup")
def lookup_barcode():
    """
    Perform a barcode lookup using the Open Food Facts API.
    This is used when a user scans a barcode; the function tries to fetch the
    product name and category from the API based on the scanned barcode.

    Returns:
        JSON: Product name, category, and a blank expiration field.
        Response codes:
            200 - Success
            400 - Bad request (no barcode provided)
            404 - Product not found
            500 - Internal server/API error
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
