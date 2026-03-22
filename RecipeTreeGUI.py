import tkinter as tk
from RecipeTree import RecipeTree, RecipeNode
from AddRecipeDialogGUI import AddRecipeDialogGUI
from util import format_stack, match_exact
from tkinter import filedialog

BG        = "#141414"
CANVAS_BG = "#0f0f0f"
NODE_BG   = "#1e1e1e"
LEAF_BG   = "#141a14"
BORDER    = "#7ec850"
LEAF_BDR  = "#2e4e2e"
EDGE_CLR  = "#2a2a2a"
TEXT_CLR  = "#d0d0c8"
DIM_CLR   = "#606060"
ACCENT    = "#7ec850"
BTN_BG    = "#1e1e1e"
FONT      = ("Consolas", 10)

NODE_W = 220
NODE_H = 64
H_GAP  = 50
V_GAP  = 100


# ── Layout ────────────────────────────────────────────
def _layout(node: RecipeNode, depth: int) -> float:
    node._y = depth * (NODE_H + V_GAP) + 60

    # Breite der Side-Outputs einrechnen
    side_extra = len(node.side_outputs) * (NODE_W + 12)

    if not node.children:
        node._x = NODE_W / 2
        return float(NODE_W) + side_extra

    widths = [_layout(c, depth + 1) for c in node.children]
    total = sum(widths) + H_GAP * (len(widths) - 1)

    cursor = 0.0
    for child, w in zip(node.children, widths):
        _shift(child, cursor)
        cursor += w + H_GAP

    node._x = (node.children[0]._x + node.children[-1]._x) / 2
    return max(total, float(NODE_W)) + side_extra

def _shift(node: RecipeNode, dx: float):
    node._x += dx
    for c in node.children:
        _shift(c, dx)

def layout_forest(roots: list):
    x_off = 40.0
    for root in roots:
        w = _layout(root, 0)
        _shift(root, x_off)
        x_off += w + 80

def all_nodes(node: RecipeNode, out=None) -> list:
    if out is None: out = []
    out.append(node)
    for c in node.children:
        all_nodes(c, out)
    return out


# ── Canvas ────────────────────────────────────────────
class TreeCanvas(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, bg=CANVAS_BG, highlightthickness=0, cursor="fleur")
        self._sc   = 1.0
        self._ox   = 0.0
        self._oy   = 0.0
        self._drag = None
        self.roots = []

        self.bind("<ButtonPress-1>", self._drag_start)
        self.bind("<B1-Motion>",     self._drag_move)
        self.bind("<MouseWheel>",    self._zoom)
        self.bind("<Button-4>",      self._zoom)
        self.bind("<Button-5>",      self._zoom)
        self.bind("<Configure>",     lambda _: self.render())
        self.bind("<Button-3>", self._on_right_click)
        self._on_delete = None  # callback: fn(item_name)
        self.bind("<Button-2>", self._on_middle_click)
        self._on_edit = None  # callback: fn(node)

    def _on_middle_click(self, e):
        wx = (e.x - self._ox) / self._sc
        wy = (e.y - self._oy) / self._sc
        for root in self.roots:
            node = self._hit_test(root, wx, wy)
            if node and self._on_edit:
                self._on_edit(node)
                return

    def _on_right_click(self, e):
        # Node unter Mauszeiger finden
        wx = (e.x - self._ox) / self._sc
        wy = (e.y - self._oy) / self._sc
        for root in self.roots:
            node = self._hit_test(root, wx, wy)
            if node:
                if self._on_delete:
                    self._on_delete(node.outputs[0].name)
                return

    def _hit_test(self, node: RecipeNode, wx: float, wy: float):
        if (abs(wx - node._x) <= NODE_W / 2 and
                abs(wy - node._y) <= NODE_H / 2):
            return node
        for c in node.children:
            hit = self._hit_test(c, wx, wy)
            if hit:
                return hit
        return None

    def w2s(self, wx, wy):
        return wx * self._sc + self._ox, wy * self._sc + self._oy

    def _drag_start(self, e): self._drag = (e.x, e.y)
    def _drag_move(self, e):
        if self._drag:
            self._ox += e.x - self._drag[0]
            self._oy += e.y - self._drag[1]
            self._drag = (e.x, e.y)
            self.render()

    def _zoom(self, e):
        f = 1.12 if (e.num == 4 or getattr(e, "delta", 0) > 0) else 1 / 1.12
        self._ox = e.x + (self._ox - e.x) * f
        self._oy = e.y + (self._oy - e.y) * f
        self._sc = max(0.15, min(self._sc * f, 4.0))
        self.render()

    def fit(self):
        nodes = [n for r in self.roots for n in all_nodes(r)]
        if not nodes: return
        min_x = min(n._x for n in nodes) - NODE_W / 2
        max_x = max(n._x for n in nodes) + NODE_W / 2
        min_y = min(n._y for n in nodes) - NODE_H / 2
        max_y = max(n._y for n in nodes) + NODE_H / 2
        cw  = max(self.winfo_width(),  800)
        ch  = max(self.winfo_height(), 600)
        pad = 50
        self._sc = max(0.2, min(
            (cw - 2*pad) / max(max_x - min_x, 1),
            (ch - 2*pad) / max(max_y - min_y, 1),
            1.5
        ))
        self._ox = pad + ((cw - 2*pad) - (max_x - min_x) * self._sc) / 2 - min_x * self._sc
        self._oy = pad - min_y * self._sc

    def load(self, roots):
        self.roots = roots
        layout_forest(self.roots)
        self.fit()
        self.render()

    def render(self):
        self.delete("all")
        if not self.roots:
            cw = max(self.winfo_width(),  400)
            ch = max(self.winfo_height(), 300)
            self.create_text(cw//2, ch//2,
                             text="No recipes yet.\nClick  +  to add one.",
                             fill="#2a2a2a", font=("Consolas", 13), justify=tk.CENTER)
            return
        for r in self.roots: self._draw_edges(r)
        for r in self.roots: self._draw_nodes(r)

    def _draw_nodes(self, node: RecipeNode):
        sx, sy = self.w2s(node._x, node._y)
        nw = NODE_W * self._sc
        nh = NODE_H * self._sc

        # Haupt-Node zeichnen
        is_leaf = not node.children
        x0, y0 = sx - nw / 2, sy - nh / 2
        x1, y1 = sx + nw / 2, sy + nh / 2
        self.create_rectangle(x0, y0, x1, y1,
                              fill=LEAF_BG if is_leaf else NODE_BG,
                              outline=LEAF_BDR if is_leaf else BORDER,
                              width=max(1, 1.5 * self._sc))
        fs = max(6, int(9 * self._sc))
        out_str = ", ".join(format_stack(s.name, node.display_amount) for s in node.outputs)
        self.create_text(sx, sy, text=out_str, fill=TEXT_CLR,
                         font=("Consolas", fs, "bold"),
                         width=nw * 0.9, justify=tk.CENTER)

        # Side-Output-Boxen nebeneinander rechts
        for i, side in enumerate(node.side_outputs):
            offset = (i + 1) * (NODE_W + 12) * self._sc
            sx2 = sx + offset
            self.create_rectangle(sx2 - nw / 2, y0, sx2 + nw / 2, y1,
                                  fill=NODE_BG, outline="#4a6e4a",
                                  width=max(1, 1.5 * self._sc))
            self.create_text(sx2, sy,
                             text=format_stack(side.name, side.amount),
                             fill=DIM_CLR, font=("Consolas", fs),
                             width=nw * 0.9, justify=tk.CENTER)
            # Horizontale Verbindung zur Haupt-Node
            self.create_line(sx + nw / 2, sy, sx2 - nw / 2, sy,
                             fill=EDGE_CLR, width=max(1.0, 1.2 * self._sc),
                             dash=(4, 4))

        for c in node.children:
            self._draw_nodes(c)

    def _draw_edges(self, node: RecipeNode):
        sx, sy = self.w2s(node._x, node._y)
        bot_y = sy + (NODE_H / 2) * self._sc

        for c in node.children:
            cx, cy = self.w2s(c._x, c._y)
            top_y = cy - (NODE_H / 2) * self._sc
            mid_y = (bot_y + top_y) / 2

            self.create_line(sx, bot_y, sx, mid_y, cx, mid_y, cx, top_y,
                             fill=EDGE_CLR, width=max(1.0, 1.4 * self._sc),
                             joinstyle=tk.ROUND)
            self._draw_edges(c)

        if node.children and node.machine:
            fs_s = max(5, int(8 * self._sc))
            label_y = bot_y + (NODE_H * 0.3) * self._sc
            self.create_text(sx, label_y, text=f"[ {node.machine} ]",
                             fill=DIM_CLR, font=("Consolas", fs_s),
                             justify=tk.CENTER)


# ── Hauptfenster ──────────────────────────────────────
class RecipeTreeGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Recipe Tree")
        self.geometry("1200x720")
        self.configure(bg=BG)
        self.tree = RecipeTree()
        self._build()
        self.after(80, self.canvas.render)

    def _build(self):
        tb = tk.Frame(self, bg="#1a1a1a", pady=8, padx=12)
        tb.pack(side=tk.TOP, fill=tk.X)

        tk.Label(tb, text="RECIPE TREE", bg="#1a1a1a", fg=ACCENT,
                 font=("Consolas", 11, "bold")).pack(side=tk.LEFT)

        tk.Button(tb, text="⊡  Fit View", command=self._fit,
                  bg=BTN_BG, fg=TEXT_CLR, relief=tk.FLAT,
                  font=FONT, padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(16, 4))

        tk.Button(tb, text="+", command=self._add,
                  bg=ACCENT, fg="#0a0a06", relief=tk.FLAT,
                  font=("Consolas", 14, "bold"), padx=12, pady=2,
                  cursor="hand2").pack(side=tk.RIGHT, padx=8)

        self.canvas = TreeCanvas(self)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # In RecipeTreeGUI._build() am Ende:
        self.canvas._on_delete = self._delete_node
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<plus>", lambda e: self._add())
        self.bind("<KP_Add>", lambda e: self._add())  # Numpad +
        tk.Button(tb, text="💾 Save", command=self._save,
                  bg=BTN_BG, fg=TEXT_CLR, relief=tk.FLAT,
                  font=FONT, padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=4)

        tk.Button(tb, text="📂 Load", command=self._load,
                  bg=BTN_BG, fg=TEXT_CLR, relief=tk.FLAT,
                  font=FONT, padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=4)
        self.canvas._on_edit = self._edit_node

    def _edit_node(self, node: RecipeNode):
        existing = self.tree.db.find(node.outputs[0].name)
        if not existing:
            return
        dlg = AddRecipeDialogGUI(self, self.tree.db, existing=existing)
        self.wait_window(dlg)
        if dlg.result:
            self.tree._save_snapshot()  # ← vor jeder Änderung
            old_name = existing.output[0].name
            new_name = dlg.result.output[0].name
            if not match_exact(old_name, new_name):
                self.tree.db.rename_ingredient(old_name, new_name)
            self.tree.db.remove(old_name)
            self.tree.db.add(dlg.result)  # direkt in DB, kein zweiter Snapshot
            self.tree._rebuild()
            self.canvas.load(self.tree.roots)

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Recipe Tree", "*.json")],
            title="Save Recipe Tree"
        )
        if path:
            self.tree.db.save(path)

    def _load(self):
        path = filedialog.askopenfilename(
            filetypes=[("Recipe Tree", "*.json")],
            title="Load Recipe Tree"
        )
        if path:
            self.tree.db.load(path)
            self.tree._rebuild()
            self.canvas.load(self.tree.roots)

    def _delete_node(self, name: str):
        self.tree.remove_recipe(name)
        self.canvas.load(self.tree.roots)

    def _undo(self):
        self.tree.undo()
        self.canvas.load(self.tree.roots)

    def _redo(self):
        self.tree.redo()
        self.canvas.load(self.tree.roots)

    def _add(self):
        dlg = AddRecipeDialogGUI(self, self.tree.db)
        self.wait_window(dlg)
        if dlg.result:
            self.tree.add_recipe(dlg.result)
            self.canvas.load(self.tree.roots)

    def _fit(self):
        self.canvas.fit()
        self.canvas.render()


if __name__ == "__main__":
    RecipeTreeGUI().mainloop()