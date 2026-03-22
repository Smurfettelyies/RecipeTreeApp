# A simple Database for the Recipe Tree, containing all, in the instance used Items and their Recipes

from Recipe import Recipe, ItemStack
from dataclasses import dataclass, field
from util import match_string, match_exact
from typing import List
import json

@dataclass
class RecipeDB:
    recipes: List[Recipe] = field(default_factory=list)

    def find_all(self, item: str) -> List[Recipe]:
        recipes_found: List[Recipe] = []
        for recipe in self.recipes:
            if any(match_string(item, stack.name) for stack in recipe.output):
                recipes_found.append(recipe)
        return recipes_found

    def find(self, item: str) -> Recipe | None:
        for recipe in self.recipes:
            if any(match_exact(item, stack.name) for stack in recipe.output):
                return recipe
        return None

    def remove(self, item: str) -> None:
        self.recipes = [r for r in self.recipes if not any(match_exact(item, s.name) for s in r.output)]

    def add(self, recipe: Recipe):
        self.recipes.append(recipe)

    def save(self, path: str) -> None:
        data = [
            {
                "machine": r.machine,
                "output": [{"name": s.name, "amount": s.amount} for s in r.output],
                "input": [{"name": s.name, "amount": s.amount} for s in r.input],
            }
            for r in self.recipes
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.recipes = [
            Recipe(
                machine=r["machine"],
                output=[ItemStack(name=s["name"], amount=s["amount"]) for s in r["output"]],
                input=[ItemStack(name=s["name"], amount=s["amount"]) for s in r["input"]],
            )
            for r in data
        ]

    def rename_ingredient(self, old_name: str, new_name: str) -> None:
        for recipe in self.recipes:
            for stack in recipe.input:
                if match_exact(stack.name, old_name):
                    stack.name = new_name