# A Recipe consisting of the Output, Input(s) and Machines (Default: Crafting Table)

from dataclasses import dataclass, field
from typing import List

@dataclass
class ItemStack:
    name: str
    amount: int = 1

@dataclass
class Recipe:
    output: List[ItemStack] = field(default_factory=list)
    input: List[ItemStack] = field(default_factory=list)
    machine: str = "Crafting Table"