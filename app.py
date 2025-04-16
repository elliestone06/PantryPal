from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json
import os
import Recipe as recipe
from datetime import datetime
from collections import defaultdict

# Initialize the Flask application
app = Flask(__name__)

# File where grocery data will be saved
data_file = 'data.json'

# ---------- Data Handling Functions ----------

def load_items():
    """
    Load grocery items from the data file (data.json).
    If the file exists, read and parse it as a list.
    If the file doesn't exist, return an empty list.
    """
    if os.path.exists(data_file):
        with open(data_file, 'r') as file:
            return json.load(file)
    return []

def save_items():
    """
    Save the current list of grocery items to the JSON file.
    This function writes the global 'items' list to disk.
    """
    with open(data_file, 'w') as file:
        json.dump(items, file, indent=4)

# Load grocery items into memory at startup
items = load_items()

# ---------- Routes ----------

@app.route("/")
def index():
    """
    Display the main inventory page.
    Groups grocery items by category and item name, and lists their expiration dates.
    Expiration dates are sorted from earliest to latest. Items without expiration dates are shown last.
    """
    # Grouping structure: {category -> {item_name -> [ {expiration, index}, ... ]}}
    grouped = defaultdict(lambda: defaultdict(list))

    # Add each item to its appropriate group
    for i, item in enumerate(items):
        category = item.get("category", "Unknown")
        name = item.get("name", "Unnamed")
        expiration = item.get("expiration", "")
        grouped[category][name].append({
            "expiration": expiration,
            "index": i  # Save original index so we can delete it later
        })

    # Sort expiration dates within each group; handle missing/invalid dates by sending them to the bottom
    for category in grouped:
        for name in grouped[category]:
            grouped[category][name].sort(
                key=lambda entry: (
                    datetime.strptime(entry["expiration"], "%Y-%m-%d")
                    if entry["expiration"] and entry["expiration"] != "Unknown"
                    else datetime.max
                )
            )

    # Sort all categories alphabetically
    sorted_grouped = dict(sorted(grouped.items()))

    # Pass grouped and sorted items to the template
    return render_template("index.html", categorized_items=sorted_grouped)

@app.route("/add", methods=["POST"])
def add_item():
    """
    Add a new grocery item submitted from the form.
    Collects item name, category, and optional expiration date.
    Saves the item and reloads the updated list.
    """
    global items

    # Get form data, clean it, and apply formatting
    name = request.form.get("item", "").strip().title()
    category = request.form.get("category", "").strip().title()
    expiration = request.form.get("expiration", "").strip() or "Unknown"

    # Only add if both name and category are provided
    if name and category:
        items.append({
            "name": name,
            "category": category,
            "expiration": expiration
        })
        save_items()       # Save updated list to file
        items = load_items()  # Reload from file to keep in sync

    return redirect(url_for("index"))

@app.route("/remove/<int:item_index>")
def remove_item(item_index):
    """
    Remove a grocery item using its index in the list.
    This is triggered when the ❌ button is clicked next to an item.
    """
    global items

    # Make sure the index is valid before trying to remove
    if 0 <= item_index < len(items):
        items.pop(item_index)   # Remove from list
        save_items()            # Save updated list
        items = load_items()    # Reload for consistency

    return redirect(url_for("index"))

@app.route("/lookup")
def lookup_barcode():
    """
    Handle barcode lookups using Open Food Facts API.
    When a user scans a barcode, this route tries to fetch the product name and category.

    Returns:
        JSON containing name, category, and empty expiration
        Status codes:
            200 - Success
            400 - Missing barcode
            404 - Product not found
            500 - API or internal error
    """
    barcode = request.args.get("barcode")
    if not barcode:
        return jsonify({}), 400  # No barcode provided

    try:
        # Query the Open Food Facts API
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url)
        data = response.json()

        # If barcode is not found in the database
        if data.get("status") != 1:
            return jsonify({}), 404

        # Extract product info
        product = data.get("product", {})
        name = product.get("product_name", "")
        category = product.get("categories_tags", [""])[0].replace("en:", "").title() if product.get("categories_tags") else ""

        return jsonify({
            "name": name,
            "category": category,
            "expiration": ""  # Leave this blank for the user to enter manually
        })

    except Exception as e:
        print("Open Food Facts API error:", e)
        return jsonify({}), 500  # Internal server error

@app.route("/recipe")
def makeRecipe():
    """
    Call the Recipe module to generate a suggested recipe based on items.
    Returns JSON data containing title, ingredients, and directions.
    """
    try:
        title, ingredients, directions = recipe.make()
        return jsonify({
            "title": title,
            "ingredients": ingredients,
            "directions": directions
        })
    except Exception as e:
        print("Recipe error:", e)
        return jsonify({}), 500

# ---------- App Runner ----------

if __name__ == "__main__":
    # Start the app in debug mode so changes auto-reload during development
    app.run(debug=True)
