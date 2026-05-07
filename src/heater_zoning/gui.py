import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .config import AnalysisConfig
from .exporters import export_summary_pdf
from .runflow import run_analysis_pipeline
from .settings import AppSettings
from .visualization import (
    build_metrics_bar_matplotlib,
    build_metrics_radar_matplotlib,
    build_module_layout_matplotlib,
    build_temperature_comparison_matplotlib,
)


class DataTree:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.tree = ttk.Treeview(self.frame, show="headings")
        self.v_scroll = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.h_scroll = ttk.Scrollbar(self.frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def populate(self, dataframe):
        self.tree.delete(*self.tree.get_children())
        columns = list(dataframe.columns)
        self.tree["columns"] = columns
        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=130, minwidth=100, anchor="center")
        for row in dataframe.itertuples(index=False):
            self.tree.insert("", "end", values=list(row))


class DesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Heater Zoning Optimizer")
        self.root.geometry("1540x940")
        self.root.minsize(1340, 820)
        self.root.configure(bg="#eef2f7")

        self.settings = AppSettings.load()
        self.current_artifacts = None

        self.source_var = tk.StringVar(value="sample")
        self.file_path_var = tk.StringVar(value=self.settings.recent_files[0] if self.settings.recent_files else "")
        self.recent_file_var = tk.StringVar(value=self.file_path_var.get())
        self.template_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="就绪")
        self.export_path_var = tk.StringVar(value="-")
        self.pdf_path_var = tk.StringVar(value="-")
        self.recommended_var = tk.StringVar(value="-")
        self._figure_canvases = []

        self._build_styles()
        self._build_layout()
        self._refresh_recent_files()
        self._refresh_templates()

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Sidebar.TFrame", background="#f8fafc")
        style.configure("Root.TFrame", background="#eef2f7")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#f8fafc", foreground="#0f172a", font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Muted.TLabel", background="#f8fafc", foreground="#475569", font=("Microsoft YaHei UI", 10))
        style.configure("Field.TLabel", background="#f8fafc", foreground="#334155", font=("Microsoft YaHei UI", 10))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#64748b", font=("Microsoft YaHei UI", 10))
        style.configure("CardValue.TLabel", background="#ffffff", foreground="#0f172a", font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Treeview", rowheight=28, font=("Microsoft YaHei UI", 10))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Accent.TButton", padding=10, font=("Microsoft YaHei UI", 10, "bold"))

    def _build_layout(self):
        wrapper = ttk.Frame(self.root, style="Root.TFrame", padding=16)
        wrapper.pack(fill="both", expand=True)
        wrapper.columnconfigure(1, weight=1)
        wrapper.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(wrapper, style="Sidebar.TFrame", padding=20)
        sidebar.grid(row=0, column=0, sticky="nsw")

        content = ttk.Frame(wrapper, style="Root.TFrame")
        content.grid(row=0, column=1, sticky="nsew", padx=(16, 0))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        self._build_sidebar(sidebar)
        self._build_content(content)

    def _build_sidebar(self, parent):
        ttk.Label(parent, text="Heater Zoning Optimizer", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(parent, text="加热分区分析台", style="Title.TLabel").pack(anchor="w", pady=(4, 8))
        ttk.Label(
            parent,
            text="桌面端用于加载温度剖面、比较分区方案、保存参数模板，并导出 Excel / PDF 摘要。",
            style="Muted.TLabel",
            wraplength=290,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        source_box = ttk.LabelFrame(parent, text="数据源", padding=12)
        source_box.pack(fill="x", pady=(0, 12))
        ttk.Radiobutton(source_box, text="示例数据", value="sample", variable=self.source_var).pack(anchor="w")
        ttk.Radiobutton(source_box, text="本地文件", value="upload", variable=self.source_var).pack(anchor="w", pady=(6, 8))
        ttk.Entry(source_box, textvariable=self.file_path_var).pack(fill="x")
        ttk.Button(source_box, text="选择文件", command=self._pick_file).pack(anchor="w", pady=(8, 0))

        ttk.Label(source_box, text="最近文件", style="Field.TLabel").pack(anchor="w", pady=(10, 2))
        self.recent_file_combo = ttk.Combobox(source_box, textvariable=self.recent_file_var, state="readonly")
        self.recent_file_combo.pack(fill="x")
        self.recent_file_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_recent_file())

        params_box = ttk.LabelFrame(parent, text="参数", padding=12)
        params_box.pack(fill="x", pady=(0, 12))
        defaults = AnalysisConfig().to_dict()
        self.entries = {}
        fields = [
            ("total_length", "总长度 (mm)"),
            ("max_zones", "最大分区数"),
            ("equal_zone_count", "等距分区数"),
            ("alpha", "梯度权重 α"),
            ("module_length", "模块长度 (mm)"),
            ("module_gap", "模块间距 (mm)"),
            ("outer_edge_allow", "边缘外伸余量 (mm)"),
        ]
        for key, label in fields:
            ttk.Label(params_box, text=label, style="Field.TLabel").pack(anchor="w")
            entry = ttk.Entry(params_box)
            entry.insert(0, str(defaults[key]))
            entry.pack(fill="x", pady=(2, 8))
            self.entries[key] = entry

        template_box = ttk.LabelFrame(parent, text="参数模板", padding=12)
        template_box.pack(fill="x", pady=(0, 12))
        self.template_combo = ttk.Combobox(template_box, textvariable=self.template_var, state="readonly")
        self.template_combo.pack(fill="x")
        ttk.Button(template_box, text="加载模板", command=self._load_template).pack(fill="x", pady=(8, 6))
        ttk.Button(template_box, text="保存当前为模板", command=self._save_template).pack(fill="x")

        ttk.Button(parent, text="运行分析", style="Accent.TButton", command=self._run_analysis).pack(fill="x", pady=(0, 10))
        ttk.Button(parent, text="导出 PDF 摘要", command=self._export_pdf_summary).pack(fill="x", pady=(0, 10))
        ttk.Button(parent, text="打开导出目录", command=self._open_output_dir).pack(fill="x")

        status_box = ttk.LabelFrame(parent, text="状态", padding=12)
        status_box.pack(fill="x", pady=(12, 0))
        ttk.Label(status_box, textvariable=self.status_var, style="Muted.TLabel", wraplength=290, justify="left").pack(anchor="w")
        ttk.Label(status_box, text="推荐方案", style="Field.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(status_box, textvariable=self.recommended_var, style="CardValue.TLabel").pack(anchor="w")
        ttk.Label(status_box, text="最近 Excel 导出", style="Field.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(status_box, textvariable=self.export_path_var, style="Muted.TLabel", wraplength=290, justify="left").pack(anchor="w")
        ttk.Label(status_box, text="最近 PDF 导出", style="Field.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(status_box, textvariable=self.pdf_path_var, style="Muted.TLabel", wraplength=290, justify="left").pack(anchor="w")

    def _build_content(self, parent):
        cards = ttk.Frame(parent, style="Root.TFrame")
        cards.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        cards.columnconfigure((0, 1, 2, 3), weight=1)
        self.card_widgets = []
        for idx in range(4):
            frame = ttk.Frame(cards, style="Card.TFrame", padding=16)
            frame.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 12, 0))
            title = ttk.Label(frame, text="-", style="CardTitle.TLabel")
            value = ttk.Label(frame, text="-", style="CardValue.TLabel")
            title.pack(anchor="w")
            value.pack(anchor="w", pady=(8, 0))
            self.card_widgets.append((title, value))

        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        self.overview_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=12)
        self.charts_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=12)
        self.tables_tab = ttk.Frame(self.notebook, style="Panel.TFrame", padding=12)
        self.notebook.add(self.overview_tab, text="概览")
        self.notebook.add(self.charts_tab, text="图表")
        self.notebook.add(self.tables_tab, text="明细表")

        self.summary_tree = DataTree(self.overview_tab)
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        self.overview_tab.columnconfigure(0, weight=1)
        self.overview_tab.rowconfigure(0, weight=1)

        self.charts_tab.columnconfigure(0, weight=1)
        self.charts_tab.rowconfigure(0, weight=1)
        self.chart_canvas = tk.Canvas(self.charts_tab, bg="#ffffff", highlightthickness=0)
        self.chart_scroll = ttk.Scrollbar(self.charts_tab, orient="vertical", command=self.chart_canvas.yview)
        self.chart_inner = ttk.Frame(self.chart_canvas, style="Panel.TFrame")
        self.chart_inner.bind("<Configure>", lambda _e: self.chart_canvas.configure(scrollregion=self.chart_canvas.bbox("all")))
        self.chart_canvas.create_window((0, 0), window=self.chart_inner, anchor="nw")
        self.chart_canvas.configure(yscrollcommand=self.chart_scroll.set)
        self.chart_canvas.grid(row=0, column=0, sticky="nsew")
        self.chart_scroll.grid(row=0, column=1, sticky="ns")

        self.tables_tab.columnconfigure(0, weight=1)
        self.tables_tab.rowconfigure(1, weight=1)
        self.tables_tab.rowconfigure(3, weight=1)
        ttk.Label(self.tables_tab, text="评价指标").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.metrics_tree = DataTree(self.tables_tab)
        self.metrics_tree.grid(row=1, column=0, sticky="nsew")
        zone_split = ttk.Panedwindow(self.tables_tab, orient="horizontal")
        zone_split.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        equal_box = ttk.LabelFrame(zone_split, text="等距分区", padding=8)
        aligned_box = ttk.LabelFrame(zone_split, text="模块对齐分区", padding=8)
        zone_split.add(equal_box, weight=1)
        zone_split.add(aligned_box, weight=1)
        self.equal_tree = DataTree(equal_box)
        self.equal_tree.grid(row=0, column=0, sticky="nsew")
        self.aligned_tree = DataTree(aligned_box)
        self.aligned_tree.grid(row=0, column=0, sticky="nsew")
        equal_box.columnconfigure(0, weight=1)
        equal_box.rowconfigure(0, weight=1)
        aligned_box.columnconfigure(0, weight=1)
        aligned_box.rowconfigure(0, weight=1)

    def _pick_file(self):
        path = filedialog.askopenfilename(filetypes=[("Data files", "*.csv *.xlsx *.xls"), ("All files", "*.*")])
        if path:
            self.file_path_var.set(path)
            self.source_var.set("upload")

    def _apply_recent_file(self):
        if self.recent_file_var.get():
            self.file_path_var.set(self.recent_file_var.get())
            self.source_var.set("upload")

    def _read_config(self):
        return AnalysisConfig(
            total_length=float(self.entries["total_length"].get()),
            max_zones=int(float(self.entries["max_zones"].get())),
            equal_zone_count=int(float(self.entries["equal_zone_count"].get())),
            alpha=float(self.entries["alpha"].get()),
            module_length=float(self.entries["module_length"].get()),
            module_gap=float(self.entries["module_gap"].get()),
            outer_edge_allow=float(self.entries["outer_edge_allow"].get()),
        ).validate()

    def _write_config(self, config: AnalysisConfig):
        payload = config.to_dict()
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(payload[key]))

    def _refresh_recent_files(self):
        self.recent_file_combo["values"] = self.settings.recent_files
        if self.settings.recent_files and not self.recent_file_var.get():
            self.recent_file_var.set(self.settings.recent_files[0])

    def _refresh_templates(self):
        names = sorted(self.settings.templates.keys())
        self.template_combo["values"] = names
        if names and self.template_var.get() not in names:
            self.template_var.set(names[0])

    def _save_template(self):
        try:
            name = simpledialog.askstring("保存模板", "请输入模板名称：", parent=self.root)
            if not name:
                return
            self.settings.save_template(name, self._read_config())
            self.settings.save()
            self._refresh_templates()
            self.template_var.set(name)
            self.status_var.set(f"模板已保存：{name}")
        except Exception as exc:
            messagebox.showerror("保存模板失败", str(exc))

    def _load_template(self):
        try:
            name = self.template_var.get()
            if not name:
                raise ValueError("请先选择模板。")
            config = self.settings.load_template(name)
            self._write_config(config)
            self.status_var.set(f"模板已加载：{name}")
        except Exception as exc:
            messagebox.showerror("加载模板失败", str(exc))

    def _run_analysis(self):
        try:
            self.status_var.set("分析中，请稍候...")
            self.root.update_idletasks()
            artifacts = run_analysis_pipeline(
                config=self._read_config(),
                source=self.source_var.get(),
                file_path=self.file_path_var.get() or None,
            )
            self.current_artifacts = artifacts
            if self.source_var.get() == "upload" and self.file_path_var.get():
                self.settings.add_recent_file(self.file_path_var.get())
                self.settings.save()
                self._refresh_recent_files()
            self.recommended_var.set(artifacts.summary_cards[0]["value"])
            self.export_path_var.set(str(artifacts.export_path))
            self.status_var.set("分析完成。图表、表格和导出文件已更新。")
            self._update_cards(artifacts.summary_cards)
            self.summary_tree.populate(artifacts.zone_summary)
            self.metrics_tree.populate(artifacts.frames.metrics)
            self.equal_tree.populate(artifacts.frames.equal_zones)
            self.aligned_tree.populate(artifacts.frames.aligned_zones)
            self._update_charts(artifacts)
            self.notebook.select(self.overview_tab)
        except Exception as exc:
            self.status_var.set("执行失败")
            messagebox.showerror("分析失败", str(exc))

    def _update_cards(self, cards):
        for idx, card in enumerate(cards):
            title, value = self.card_widgets[idx]
            title.configure(text=card["label"])
            value.configure(text=card["value"])

    def _clear_charts(self):
        for canvas, figure in self._figure_canvases:
            canvas.get_tk_widget().destroy()
            figure.clf()
        self._figure_canvases.clear()

    def _add_figure(self, figure, row, column, colspan=1):
        canvas = FigureCanvasTkAgg(figure, master=self.chart_inner)
        widget = canvas.get_tk_widget()
        widget.grid(row=row, column=column, columnspan=colspan, sticky="nsew", padx=8, pady=8)
        canvas.draw()
        self._figure_canvases.append((canvas, figure))

    def _update_charts(self, artifacts):
        self._clear_charts()
        for col in (0, 1):
            self.chart_inner.columnconfigure(col, weight=1)

        result = artifacts.result
        self._add_figure(build_temperature_comparison_matplotlib(result.profile_df, result.equal_zones, result.aligned_zones), 0, 0, 2)
        self._add_figure(build_module_layout_matplotlib(result.equal_zones, result.aligned_zones), 1, 0, 2)
        self._add_figure(build_metrics_bar_matplotlib(result.equal_metrics, result.aligned_metrics), 2, 0)
        self._add_figure(build_metrics_radar_matplotlib(result.equal_metrics, result.aligned_metrics), 2, 1)

    def _export_pdf_summary(self):
        try:
            if not self.current_artifacts:
                raise ValueError("请先运行一次分析。")
            default_name = f"heater_zoning_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialdir=str(Path("outputs").resolve()),
                initialfile=default_name,
                filetypes=[("PDF files", "*.pdf")],
            )
            if not path:
                return
            export_path = export_summary_pdf(self.current_artifacts.result, Path(path))
            self.pdf_path_var.set(str(export_path))
            self.status_var.set("PDF 摘要导出完成。")
        except Exception as exc:
            messagebox.showerror("导出 PDF 失败", str(exc))

    def _open_output_dir(self):
        output_dir = Path("outputs").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(output_dir)


def launch():
    root = tk.Tk()
    app = DesktopApp(root)
    app._run_analysis()
    root.mainloop()
