from transformers import FlaxAutoModelForSeq2SeqLM, AutoTokenizer
import json

DEBUG = False


def make():
# Opening data file
    with open('data.json','r') as file:
        data = json.load(file)

    # Load model and tokenizer
    model = FlaxAutoModelForSeq2SeqLM.from_pretrained("flax-community/t5-recipe-generation")
    tokenizer = AutoTokenizer.from_pretrained("flax-community/t5-recipe-generation")

    # making list of item names and formatting to work with the generator
    items = []
    for item in data:
        items.append(item["name"])
    items = ", ".join(items)

    if DEBUG:
        print(items)


    # Format input
    input_text = f"items: {items}"

    # Tokenize
    inputs = tokenizer(
        input_text,
        max_length=256,
        padding="max_length",
        truncation=True,
        return_tensors="jax"
    )

    # Generate
    output_ids = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_length=512,
        do_sample=True,
        top_p=0.95
    ).sequences


    # Decode
    recipe = str(tokenizer.decode(output_ids[0], skip_special_tokens=True))

    #formatting!! Making the different parts of the recipe into individual variables
    title = recipe[recipe.index("title:") + 7 : recipe.index("ingredients: ")]
    ingredients = recipe[recipe.index("ingredients:") + 13: recipe.index("directions: ")]
    directions = recipe[recipe.index("directions:")+12:]

    if DEBUG:
        print(f"{title}\n\n{ingredients}\n\n{directions}")

    return title, ingredients, directions




############### How to use Function ##############
#import Recipe

#title, ingredients, directions = Recipe.make()

