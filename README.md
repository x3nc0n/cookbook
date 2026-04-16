# The Cookbook

A GitHub Pages–hosted recipe collection with automatic tagging and classification.

## Adding Recipes

Install Python dependencies once:

```bash
pip install -r requirements.txt
```

Then add recipes using any of these methods:

### From a URL
```bash
python scripts/add_recipe.py --url "https://www.allrecipes.com/recipe/12345/"
```

### From a local HTML or text file
```bash
python scripts/add_recipe.py --file path/to/recipe.html
python scripts/add_recipe.py --text path/to/recipe.txt
```

### Interactive entry
```bash
python scripts/add_recipe.py -i
```

### Plain text format
When using `--text`, structure your file like this:

```
Recipe Title

Description
A short description of the dish.

Ingredients
- 1 cup flour
- 2 eggs
- 1/2 cup milk

Instructions
1. Mix dry ingredients.
2. Add wet ingredients and stir.
3. Cook until done.
```

## Auto-Tagging

The script automatically classifies recipes by:
- **Dish type**: Cocktail, Entrée, Side, Appetizer, Dessert, Soup, Salad, Breakfast, Bread, Sauce
- **Cuisine**: Italian, Mexican, Chinese, Japanese, Indian, Thai, French, Mediterranean, Korean, American, Spanish, Vietnamese, Greek
- **Main ingredient**: Chicken, Beef, Pork, Fish, Shellfish, Pasta, Rice, Eggs, Tofu, Beans, Vegetables
- **Dietary tags**: Vegetarian, Vegan, Gluten-Free

## Local Development

```bash
bundle install
bundle exec jekyll serve
```

Then visit `http://localhost:4000`.

## Deploying

Push to GitHub and enable GitHub Pages in your repository settings (deploy from the `main` branch root `/`).
