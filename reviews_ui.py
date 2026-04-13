import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from parse_pasted_reviews import parse_reviews, write_reviews_csv


DEFAULT_OUTPUT = "parsed_reviews.csv"


class ReviewsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Amazon Review Parser")
        self.root.geometry("1200x700")
        self.root.minsize(900, 560)
        self._setup_style()
        self.records = []

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        top_bar = tk.Frame(root, bg="#f5f6f7")
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        ttk.Button(top_bar, text="Parse", command=self.parse_input).pack(side="left", padx=(0, 8))
        ttk.Button(top_bar, text="Save CSV", command=self.save_csv).pack(side="left")
        ttk.Label(top_bar, text="Left: paste raw reviews  |  Right: parsed result").pack(side="right")

        panes = tk.PanedWindow(root, orient="horizontal", sashrelief="raised", bd=0, bg="#f5f6f7")
        panes.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        left_frame = tk.LabelFrame(panes, text="Raw Input", padx=8, pady=8, bg="#f5f6f7", fg="#111111")
        right_frame = tk.LabelFrame(panes, text="Parsed Reviews", padx=8, pady=8, bg="#f5f6f7", fg="#111111")
        panes.add(left_frame, stretch="always", minsize=340)
        panes.add(right_frame, stretch="always", minsize=420)

        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        self.input_text = tk.Text(
            left_frame,
            wrap="word",
            font=("Menlo", 12),
            bg="#ffffff",
            fg="#111111",
            insertbackground="#111111",
            relief="solid",
            borderwidth=1,
        )
        self.input_text.grid(row=0, column=0, sticky="nsew")
        self.input_text.insert("1.0", "Paste Amazon review text here...\n")

        columns = ("rating", "title", "content")
        self.result_table = ttk.Treeview(
            right_frame,
            columns=columns,
            show="headings",
            height=18,
        )
        self.result_table.heading("rating", text="Rating")
        self.result_table.heading("title", text="Title")
        self.result_table.heading("content", text="Content")
        self.result_table.column("rating", width=70, anchor="center")
        self.result_table.column("title", width=240, anchor="w")
        self.result_table.column("content", width=520, anchor="w")

        y_scroll = ttk.Scrollbar(right_frame, orient="vertical", command=self.result_table.yview)
        x_scroll = ttk.Scrollbar(right_frame, orient="horizontal", command=self.result_table.xview)
        self.result_table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.result_table.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=(0, 2))
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        right_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready")
        status = ttk.Label(root, textvariable=self.status_var, anchor="w")
        status.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

    def _setup_style(self) -> None:
        # Force light palette so the UI stays readable even in dark-mode Tk variants.
        self.root.configure(bg="#f5f6f7")
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(".", background="#f5f6f7", foreground="#111111")
        style.configure("TLabelframe", background="#f5f6f7", foreground="#111111")
        style.configure("TLabelframe.Label", background="#f5f6f7", foreground="#111111")
        style.configure("TLabel", background="#f5f6f7", foreground="#111111")
        style.configure("TButton", background="#ffffff", foreground="#111111")

        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#111111",
            rowheight=24,
        )
        style.configure(
            "Treeview.Heading",
            background="#e9ecef",
            foreground="#111111",
            relief="flat",
        )

    def parse_input(self) -> None:
        raw = self.input_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("No input", "Please paste raw review text on the left side.")
            return

        self.records = parse_reviews(raw)
        self._refresh_table()
        self.status_var.set(f"Parsed {len(self.records)} reviews.")

    def _refresh_table(self) -> None:
        for item in self.result_table.get_children():
            self.result_table.delete(item)

        for row in self.records:
            self.result_table.insert(
                "",
                "end",
                values=(
                    row.get("rating", ""),
                    row.get("title", ""),
                    row.get("content", "").replace("\n", " "),
                ),
            )

    def save_csv(self) -> None:
        if not self.records:
            messagebox.showwarning("No parsed data", "Please click Parse first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save parsed CSV",
            initialfile=DEFAULT_OUTPUT,
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        write_reviews_csv(self.records, path)
        self.status_var.set(f"Saved {len(self.records)} reviews to {path}")
        messagebox.showinfo("Saved", f"CSV saved:\n{path}")


def main() -> None:
    root = tk.Tk()
    app = ReviewsApp(root)
    app.status_var.set("Paste text on the left, then click Parse.")
    root.mainloop()


if __name__ == "__main__":
    main()
