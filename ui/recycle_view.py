import tkinter as tk
from tkinter import ttk
from config import C

class RecycleView(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._items = []
        self._build_ui()

    def _build_ui(self):
        sb = ttk.Scrollbar(self, orient="vertical")
        sb.pack(side="right", fill="y")

        self.cv = tk.Canvas(self, bg=C["bg"], highlightthickness=0,
                            yscrollcommand=sb.set)
        self.cv.pack(side="left", fill="both", expand=True)
        sb.config(command=self.cv.yview)

        self.inner = tk.Frame(self.cv, bg=C["bg"])
        self._wid  = self.cv.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>",
            lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>",
            lambda e: self.cv.itemconfig(self._wid, width=e.width))

        self.cv.bind_all("<MouseWheel>", self._scroll)
        self.cv.bind_all("<Button-4>",   self._scroll)
        self.cv.bind_all("<Button-5>",   self._scroll)

    def _scroll(self, e):
        if   e.num == 4: self.cv.yview_scroll(-1, "units")
        elif e.num == 5: self.cv.yview_scroll( 1, "units")
        else:            self.cv.yview_scroll(int(-e.delta / 120), "units")

    def add(self, w):
        self._items.append(w)
        w.pack(in_=self.inner, fill="x", padx=14, pady=(0, 8))
        self.inner.update_idletasks()
        self.cv.configure(scrollregion=self.cv.bbox("all"))

    def items(self):
        return self._items

    def clear(self):
        for w in self._items: w.destroy()
        self._items.clear()