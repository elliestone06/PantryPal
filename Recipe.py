from google import genai
import json

DEBUG = False

client = genai.Client(api_key="AIzaSyCOiJUmQMDmEVS2Q7AIQYD4rgsaev5KzBg")

def make():
# Opening data file
    with open('data.json','r') as file:
        data = json.load(file)

    # making list of item names and formatting to work with the generator
    items = []
    for item in data:
        items.append(item["name"])
    items = ", ".join(items)

    if DEBUG:
        print(items)

    # Asking Gemini API for a recipe in a useable format
    response = client.models.generate_content(
    model="gemini-2.0-flash", contents=f"Generate a recipe using these ingredients: {items}. Only have Title, Ingredients, and Directions sections without any added fluff or sentences. Not all ingredients must be used."
    )

    if DEBUG:
        print(response.text)    

    # formatting!!!
    title = str(response.text[:response.text.index("\n")])
    title= title.strip("*")

    ingredients = str(response.text[response.text.index("**Ingredients:**\n")+16:response.text.index("\n**Directions:**")])
    ingredients = ingredients.strip()

    directions = str(response.text[response.text.index("**Directions:**\n")+15:])
    directions = directions.strip()

    if DEBUG:
        print(title)
        print(ingredients)
        print(directions)

    return title, ingredients, directions
make()
