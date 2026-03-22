# A recipe tree
from bdb import effective

from RecipeDB import RecipeDB
from Recipe import Recipe, ItemStack
from dataclasses import dataclass, field
from typing import List
from util import match_exact
from copy import deepcopy

@dataclass
class RecipeNode:
    machine:        str
    outputs:        List[ItemStack] = field(default_factory=list)
    side_outputs:   List[ItemStack] = field(default_factory=list)
    children:       List['RecipeNode'] = field(default_factory=list)
    display_amount: int = 1

    @property
    def label(self) -> str:
        outs = ", ".join(format_stack(s.name, s.amount) for s in self.outputs)
        return f"{outs} <-- {self.machine}"

    def produces(self, name: str) -> bool:
        return any(s.name.lower() == name.lower() for s in self.outputs)

    def add_child(self, child: 'RecipeNode'):
        self.children.append(child)

@dataclass
class RecipeTree:
    roots: List[RecipeNode] = field(default_factory=list)
    db: RecipeDB = field(default_factory=RecipeDB)
    _undo_stack: List = field(default_factory=list)
    _redo_stack: List = field(default_factory=list)

    def recipe_to_node(self, recipe: Recipe, multiplier: int = 1, for_ingredient: str = None) -> RecipeNode:
        output_amount = recipe.output[0].amount if recipe.output else 1

        # Welcher Output ist der gesuchte?
        if for_ingredient:
            main_out = next((s for s in recipe.output if match_exact(s.name, for_ingredient)), recipe.output[0])
            output_amount = main_out.amount
        else:
            main_out = recipe.output[0] if recipe.output else None

        batches = multiplier / output_amount if output_amount else 1

        if for_ingredient:
            side_outs = [ItemStack(name=s.name, amount=int(s.amount * batches))
                         for s in recipe.output if not match_exact(s.name, for_ingredient)]
        else:
            side_outs = [ItemStack(name=s.name, amount=int(s.amount * batches))
                         for s in recipe.output[1:]]

        node = RecipeNode(
            machine=recipe.machine,
            outputs=[main_out] if main_out else [],
            side_outputs=side_outs,
            display_amount=multiplier
        )
        for ing in recipe.input:
            child_recipe = self.db.find(ing.name)
            effective_amount = int(ing.amount * batches)
            if child_recipe is not None:
                node.add_child(self.recipe_to_node(child_recipe,
                                                   multiplier=effective_amount,
                                                   for_ingredient=ing.name))
            else:
                node.add_child(RecipeNode(
                    machine="",
                    outputs=[ItemStack(name=ing.name, amount=ing.amount)],
                    display_amount=effective_amount
                ))
        return node

    def find_node(self, name:str) -> RecipeNode | None:
        stack = list(self.roots)
        while stack:
            node = stack.pop()
            if any(match_exact(name, s.name) for s in node.outputs):
                return node
            stack.extend(node.children)
        return None

    def _iter(self, node: RecipeNode):
        yield node
        for child in node.children:
            yield from self._iter(child)

    def _clean_roots(self):
        all_children = {s.name
                        for root in self.roots
                        for node in self._iter(root)
                        for child in node.children
                        for s in child.outputs}
        self.roots = [r for r in self.roots if not any(s.name in all_children for s in r.outputs)]

    def merge_nodes(self, node: RecipeNode) -> None:
        for i, child in enumerate(node.children):
            for s in child.outputs:
                child_recipe = self.db.find(s.name)
                if child_recipe is not None:
                    node.children[i] = self.recipe_to_node(
                        child_recipe,
                        multiplier=child.display_amount  # ← Multiplikator erhalten
                    )
                    break
            else:
                self.merge_nodes(child)

    def _save_snapshot(self):
        self._undo_stack.append(deepcopy(self.db.recipes))
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(deepcopy(self.db.recipes))
        self.db.recipes = self._undo_stack.pop()
        self._rebuild()

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(deepcopy(self.db.recipes))
        self.db.recipes = self._redo_stack.pop()
        self._rebuild()

    def _rebuild(self):
        self.roots.clear()
        for recipe in self.db.recipes:
            self.roots.append(self.recipe_to_node(recipe))
        for root in self.roots:
            self.merge_nodes(root)
        self._clean_roots()

    def add_recipe(self, recipe: Recipe):
        self._save_snapshot()
        self.db.add(recipe)
        self.roots.append(self.recipe_to_node(recipe))
        for root in self.roots:
            self.merge_nodes(root)
        self._clean_roots()

    def remove_recipe(self, item: str) -> None:
        self._save_snapshot()
        self.db.remove(item)
        self._rebuild()