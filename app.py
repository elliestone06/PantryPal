from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json
import os
from datetime import datetime
from collections import defaultdict

# Initialize the Flask application
app = Flask(__name__)

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

@app.route("/")
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
    for category in categorized:
        for name in categorized[category]:
            categorized[category][name].sort(
                key=lambda entry: datetime.strptime(entry["expiration"], "%Y-%m-%d") if entry["expiration"] else datetime.max
            )

    # Sort categories alphabetically for display
    sorted_categorized = dict(sorted(categorized.items()))

    return render_template("index.html", categorized_items=sorted_categorized)

@app.route("/add", methods=["POST"])
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

if __name__ == "__main__":
    # Run the app in debug mode for development/testing
    app.run(debug=True)
