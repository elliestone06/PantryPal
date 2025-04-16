from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json
import os
import Recipe as recipe
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

data_file = 'data.json'

def load_items():
    if os.path.exists(data_file):
        with open(data_file, 'r') as file:
            return json.load(file)
    return []

def save_items():
    with open(data_file, 'w') as file:
        json.dump(items, file, indent=4)

# Global list of items, initially loaded from file
items = load_items()

@app.route("/")
def index():
    categorized = defaultdict(lambda: defaultdict(list))
    for i, item in enumerate(items):
        category = item.get("category", "Unknown")
        name = item.get("name", "Unnamed")
        expiration = item.get("expiration", "")
        categorized[category][name].append({"expiration": expiration, "index": i, "name": name, "category": category})

    # Sort expiration dates
    for cat in categorized:
        for name in categorized[cat]:
            categorized[cat][name].sort(
                key=lambda x: datetime.strptime(x["expiration"], "%Y-%m-%d") if x["expiration"] else datetime.max
            )

    sorted_categorized = dict(sorted(categorized.items()))

    return render_template("index.html", categorized_items=sorted_categorized)

@app.route("/add", methods=["POST"])
def add_item():
    global items
    name = request.form.get("item", "").strip().title()
    category = request.form.get("category", "").strip().title()
    expiration = request.form.get("expiration", "").strip() or "Unknown"

    if name and category:
        items.append({"name": name, "category": category, "expiration": expiration})
        save_items()
        items = load_items()

    return redirect(url_for("index"))

@app.route("/remove/<int:item_index>")
def remove_item(item_index):
    global items
    if 0 <= item_index < len(items):
        items.pop(item_index)
        save_items()
        items = load_items()
    return redirect(url_for("index"))

@app.route("/lookup")
def lookup_barcode():
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
    try:
        title, ingredients, directions = recipe.make()
        return jsonify({
            "title": title,
            "ingredients": ingredients,
            "directions" : directions
        })
    except Exception as e:
        print("Recipe error:", e)
        return jsonify({}), 500

if __name__ == "__main__":
    app.run(debug=True)
