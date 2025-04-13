from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json
import os
import Recipe as recipe

# Create the Flask app instance
app = Flask(__name__)

# Path to the file that will store grocery items (this simulates a database)
data_file = 'data.json'

# Function to load the items from our data file when the app starts
def load_items():
    """
    This function is responsible for loading the saved grocery list items from
    the data.json file. If the file exists, it reads the JSON data and returns it.
    If the file doesn't exist (for the first run or after deletion), it returns an empty list.
    """
    if os.path.exists(data_file):  # Check if the data.json file exists
        with open(data_file, 'r') as file:
            return json.load(file)  # Read and return the list of items from the file
    return []  # If the file doesn't exist, return an empty list

# Function to save the current list of items into the data file
def save_items():
    """
    This function is responsible for saving the current grocery list to the
    data.json file. It serializes the items into JSON format and writes them to the file.
    """
    with open(data_file, 'w') as file:
        json.dump(items, file, indent=4)  # Save the items list to the file in a human-readable format

# Load the items from the data file when the app starts up
items = load_items()

@app.route("/")
def index():
    """
    This route handles the display of the main page of the app. It passes the list
    of grocery items to the HTML template so that users can view their saved items.
    """
    return render_template("index.html", items=items)  # Pass the current list of items to the template

@app.route("/add", methods=["POST"])
def add_item():
    """
    This route handles the form submission when a user adds a new item manually.
    The item name, category, and expiration date are extracted from the form, formatted,
    and added to the in-memory list of items. After adding the item, the list is saved
    to the data.json file to preserve the new item across restarts.
    """
    # Extract item details from the form input, ensuring capitalization for consistency
    name = request.form.get("item", "").strip().title()  # Capitalize the item name
    category = request.form.get("category", "").strip().title()  # Capitalize the category (shoudln't matter because it's a dropdown)
    expiration = request.form.get("expiration", "").strip()  # Extract the expiration date

    # Add the new item to the list
    items.append({"name": name, "category": category, "expiration": expiration})

    # Save the updated list of items to the data file
    save_items()

    # Redirect back to the index page
    return redirect(url_for("index"))

@app.route("/remove/<int:item_index>")
def remove_item(item_index):
    """
    This route handles the deletion of an item from the grocery list.
    The item is removed from the in-memory list using the given index.
    After removing the item, the updated list is saved back to the data file.
    """
    # Make sure the index is valid before trying to remove the item
    if 0 <= item_index < len(items):
        items.pop(item_index)  # Remove the item by index
        save_items()  # Save the updated list to data.json

    # Redirect to the main page to refresh the list
    return redirect(url_for("index"))

@app.route("/lookup")
def lookup_barcode():
    """
    This route is triggered by a barcode scan. It queries the Open Food Facts API
    to fetch product details based on the barcode and returns the product's name, category,
    and a blank expiration field to be filled manually.
    """
    barcode = request.args.get("barcode")
    if not barcode:
        return jsonify({}), 400  # Bad request if no barcode is passed

    try:
        # Construct the URL to hit the Open Food Facts API using the scanned barcode
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        response = requests.get(url)
        data = response.json()

        # If product is not found in the API
        if data.get("status") != 1:
            return jsonify({}), 404

        product = data.get("product", {})

        # Get the product name (or empty if not found)
        name = product.get("product_name", "")

        # Get the first category tag (removing language prefix) or empty if missing
        category = product.get("categories_tags", [""])[0].replace("en:", "").title() if product.get("categories_tags") else ""

        # Return the name and category to prefill the form. Expiration is left blank as Open Food Facts doesn’t provide it.
        return jsonify({
            "name": name,
            "category": category,
            "expiration": ""  # Expiration date must still be entered manually
        })
    except Exception as e:
        # Print any errors to the terminal for debugging
        print("Open Food Facts API error:", e)
        return jsonify({}), 500  # Internal server error
    
@app.route("/recipe")
def makeRecipe():
    title, ingredients, directions = recipe.make()
    return jsonify({
        "title": title,
        "ingredients": ingredients,
        "directions" : directions
    })

if __name__ == "__main__":
    # Run the app in debug mode (useful for development and testing)
    app.run(debug=True)
