import tkinter as tk
from tkinter import messagebox
from Recipe import Recipe, ItemStack
from RecipeDB import RecipeDB
from util import parse_amount, capitalize_name

BG       = "#141414"
FG       = "#d0d0c8"
ACCENT   = "#7ec850"
ENTRY_BG = "#1e1e1e"
BTN_BG   = "#252525"
DIM      = "#606060"
FONT     = ("Consolas", 10)
FONT_B   = ("Consolas", 10, "bold")


class AcEntry(tk.Frame):
    def __init__(self, parent, suggest_fn, width=22, **kw):
        super().__init__(parent, bg=ENTRY_BG, **kw)
        self._suggest = suggest_fn
        self._popup   = None
        self._lb      = None

        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, width=width,
                              bg=ENTRY_BG, fg=FG, insertbackground=FG,
                              relief=tk.FLAT, font=FONT, bd=0)
        self.entry.pack(fill=tk.BOTH, expand=True, padx=5, pady=4)

        self.var.trace_add("write", lambda *_: self.after(100, self._update))
        self.entry.bind("<Down>",    self._focus_lb)
        self.entry.bind("<Return>",  self._on_entry_return)
        self.entry.bind("<Escape>",  lambda e: self._close())
        self.entry.bind("<FocusOut>", lambda e: self.after(150, self._maybe_close))

    def _on_entry_return(self, e):
        if self._lb:
            self._pick()
        else:
            self.event_generate("<<ConfirmDialog>>")
            # Fokus zum Toplevel damit dessen <Return> feuert
            parent = self.winfo_toplevel()
            parent.event_generate("<Return>")

    def get(self):    return capitalize_name(self.var.get())
    def set(self, v): self.var.set(v)
    def focus(self):  self.entry.focus_set()

    def _on_entry_return(self, e):
        if self._lb:
            self._pick()
        # wenn kein Dropdown offen: nichts tun, Dialog-Confirm greift

    def _update(self):
        hits = self._suggest(self.var.get())
        if not hits or (len(hits) == 1 and hits[0].lower() == self.var.get().lower()):
            self._close()
        else:
            self._open(hits)

    def _tab_complete(self, e):
        if self._lb and self._lb.size() > 0:
            self.var.set(self._lb.get(0))
            self._close()
            return "break"  # verhindert dass Tab den Fokus wechselt

    def _open(self, items):
        self._close()
        self.entry.update_idletasks()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height() + 1
        self._popup = tk.Toplevel(self.entry)
        self._popup.wm_overrideredirect(True)
        self._popup.wm_geometry(f"+{x}+{y}")
        self._popup.attributes("-topmost", True)
        self._lb = tk.Listbox(self._popup, bg="#1e1e1e", fg=FG,
                              selectbackground="#2e4e2e", selectforeground=ACCENT,
                              relief=tk.FLAT, bd=0, font=FONT,
                              height=min(6, len(items)), width=self.entry["width"],
                              activestyle="none", exportselection=False)
        self._lb.pack()
        for item in items:
            self._lb.insert(tk.END, item)
        self._lb.bind("<Return>",          lambda e: self._pick())
        self._lb.bind("<Double-Button-1>", lambda e: self._pick())
        self._lb.bind("<Up>",              self._lb_up)
        self._lb.bind("<Escape>",          lambda e: self._close())
        self._lb.bind("<FocusOut>",        lambda e: self.after(150, self._maybe_close))
        self._lb.bind("<Tab>", lambda e: self._pick())
        self.entry.bind("<Tab>", self._tab_complete)

    def _lb_up(self, e):
        if self._lb and self._lb.curselection() == (0,):
            self._close()
            self.entry.focus_set()

    def _pick(self):
        if self._lb:
            sel = self._lb.curselection()
            if sel:
                self.var.set(self._lb.get(sel[0]))
        self._close()
        self.entry.focus_set()

    def _focus_lb(self, *_):
        if self._lb:
            self._lb.focus_set()
            self._lb.selection_clear(0, tk.END)
            self._lb.selection_set(0)
            self._lb.activate(0)

    def _maybe_close(self):
        try:
            fw = self.focus_get()
        except Exception:
            fw = None
        if fw is not self._lb and fw is not self.entry:
            self._close()

    def _close(self):
        if self._popup:
            self._popup.destroy()
            self._popup = None
            self._lb    = None

class StackRow(tk.Frame):
    """Eine Zeile: [Name Autocomplete] -- [Amount]"""
    def __init__(self, parent, suggest_fn, on_change, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.name_entry = AcEntry(self, suggest_fn, width=22)
        self.name_entry.pack(side=tk.LEFT)
        self.name_entry.var.trace_add("write", lambda *_: on_change())

        tk.Label(self, text="--", bg=BG, fg=DIM, font=FONT).pack(side=tk.LEFT, padx=6)

        self.amt_var = tk.StringVar(value="1")
        tk.Entry(self, textvariable=self.amt_var, width=5,
                 bg=ENTRY_BG, fg=FG, insertbackground=FG,
                 relief=tk.FLAT, font=FONT, bd=0).pack(side=tk.LEFT, ipady=4)

    def get(self) -> ItemStack | None:
        name = self.name_entry.get()
        if not name:
            return None
        return ItemStack(name=name, amount=parse_amount(self.amt_var.get()))

    def is_empty(self) -> bool:
        return self.name_entry.get() == ""


class StackSection(tk.Frame):
    """Dynamische Liste von StackRows mit Auto-Expand."""
    def __init__(self, parent, suggest_fn, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._suggest = suggest_fn
        self._rows: list[StackRow] = []
        self._add_row()

    def _add_row(self):
        row = StackRow(self, self._suggest, self._on_change)
        row.pack(fill=tk.X, pady=2)
        self._rows.append(row)

    def _on_change(self):
        if self._rows and not self._rows[-1].is_empty():
            self._add_row()

    def get_stacks(self) -> list[ItemStack]:
        return [r.get() for r in self._rows if not r.is_empty()]


class AddRecipeDialogGUI(tk.Toplevel):
    def __init__(self, parent, db: RecipeDB, existing: Recipe = None):
        super().__init__(parent)
        self.db = db
        self.existing = existing
        self.result: Recipe | None = None

        self.title("Add Recipe")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self._build()
        self._center(parent)

    def _suggest_names(self, text: str) -> list[str]:
        names = {s.name for r in self.db.recipes for s in r.output + r.input}
        from util import match_string
        return sorted(n for n in names if match_string(text, n))

    def _suggest_machines(self, text: str) -> list[str]:
        machines = {r.machine for r in self.db.recipes}
        from util import match_string
        return sorted(m for m in machines if match_string(text, m))

    def _build(self):
        tk.Label(self, text="ADD RECIPE", bg=BG, fg=ACCENT,
                 font=("Consolas", 12, "bold")).pack(pady=(18, 12))

        tk.Label(self, text="Machine", bg=BG, fg=DIM, font=FONT).pack(anchor="w", padx=20)
        self._mach = AcEntry(self, self._suggest_machines, width=32)
        self._mach.pack(padx=20, pady=(0, 12), fill=tk.X)

        tk.Label(self, text="Output(s)", bg=BG, fg=DIM, font=FONT).pack(anchor="w", padx=20)
        self._outputs = StackSection(self, self._suggest_names)
        self._outputs.pack(padx=20, fill=tk.X)

        tk.Label(self, text="Input(s)", bg=BG, fg=DIM, font=FONT).pack(anchor="w", padx=20, pady=(10, 0))
        self._inputs = StackSection(self, self._suggest_names)
        self._inputs.pack(padx=20, fill=tk.X)

        bf = tk.Frame(self, bg=BG)
        bf.pack(pady=16)
        tk.Button(bf, text="✓ Confirm", command=self._confirm,
                  bg=ACCENT, fg="#0a0a06", relief=tk.FLAT,
                  font=FONT_B, padx=12, pady=6, cursor="hand2").pack(side=tk.LEFT, padx=6)
        tk.Button(bf, text="✕ Cancel", command=self.destroy,
                  bg=BTN_BG, fg=FG, relief=tk.FLAT,
                  font=FONT, padx=12, pady=6, cursor="hand2").pack(side=tk.LEFT, padx=6)

        self._mach.focus()
        self.bind("<Return>", lambda e: self._confirm())
        self._mach.entry.bind("<Return>", lambda e: self._confirm())
        if self.existing:
            self._prefill()

    def _prefill(self):
        r = self.existing
        self._mach.set(r.machine)

        # Outputs vorausfüllen
        for i, stack in enumerate(r.output):
            if i >= len(self._outputs._rows):
                self._outputs._add_row()
            row = self._outputs._rows[i]
            row.name_entry.set(stack.name)
            row.amt_var.set(str(stack.amount))

        # Inputs vorausfüllen
        for i, stack in enumerate(r.input):
            if i >= len(self._inputs._rows):
                self._inputs._add_row()
            row = self._inputs._rows[i]
            row.name_entry.set(stack.name)
            row.amt_var.set(str(stack.amount))

    def _confirm(self):
        machine = self._mach.get() or "Crafting Table"
        outputs = self._outputs.get_stacks()
        inputs  = self._inputs.get_stacks()

        if not machine:
            messagebox.showwarning("Missing", "Machine is required.", parent=self)
            return
        if not outputs:
            messagebox.showwarning("Missing", "At least one output is required.", parent=self)
            return

        self.result = Recipe(output=outputs, input=inputs, machine=machine)
        self.destroy()

    def _center(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")