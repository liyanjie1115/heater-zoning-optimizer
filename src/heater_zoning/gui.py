from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .branding import APP_DESCRIPTION_ZH, APP_NAME_EN, APP_NAME_ZH
from .config import AnalysisConfig
from .exporters import export_summary_pdf
from .reporting import (
    build_config_snapshot,
    build_decision_overview,
)
from .runflow import run_analysis_pipeline
from .settings import AppSettings
from .visualization import (
    build_metrics_bar_matplotlib,
    build_metrics_radar_matplotlib,
    build_module_layout_matplotlib,
    build_temperature_comparison_matplotlib,
)


PRESET_CONFIGS = {
    "balanced": {"label": "平衡推荐", "overrides": {}},
    "precision": {
        "label": "追求贴合",
        "overrides": {"gradient_weight": 0.30, "fit_weight": 0.36, "heater_weight": 0.10, "balance_weight": 0.08},
    },
    "installation": {
        "label": "优先安装",
        "overrides": {"heater_weight": 0.22, "balance_weight": 0.14, "fit_weight": 0.24, "gradient_weight": 0.18},
    },
    "compact": {
        "label": "控制分区/模块复杂度",
        "overrides": {"max_zones": 6, "equal_zone_count": 6, "balance_weight": 0.16, "heater_weight": 0.16},
    },
}


APP_STYLESHEET = """
QWidget {
    background: #eef3f8;
    color: #0f172a;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow {
    background: #eef3f8;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    margin-top: 14px;
    font-weight: 600;
    padding-top: 10px;
}
QGroupBox::title {
    left: 14px;
    padding: 0 4px;
    color: #475569;
}
QLineEdit, QComboBox, QTableWidget, QTabWidget::pane {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
}
QLineEdit, QComboBox {
    min-height: 38px;
    padding: 0 10px;
}
QPushButton {
    min-height: 40px;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    background: #ffffff;
    padding: 0 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #f8fbff;
}
QPushButton[role="primary"] {
    background: #2563eb;
    border-color: #2563eb;
    color: white;
}
QPushButton[role="primary"]:hover {
    background: #1d4ed8;
}
QTabBar::tab {
    background: #f8fafc;
    border: 1px solid #d9e2ec;
    border-bottom: 0;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 16px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0f172a;
}
QHeaderView::section {
    background: #f8fafc;
    color: #334155;
    border: 0;
    border-bottom: 1px solid #d9e2ec;
    padding: 8px;
    font-weight: 600;
}
QTableWidget {
    gridline-color: #e2e8f0;
    alternate-background-color: #f8fafc;
}
QScrollArea {
    border: 0;
    background: transparent;
}
QListWidget {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    padding: 4px;
}
"""


class CardWidget(QFrame):
    def __init__(self, title: str, accent: str = "#ffffff"):
        super().__init__()
        self.setObjectName("summaryCard")
        self.setStyleSheet(
            f"""
            QFrame#summaryCard {{
                background: {accent};
                border: 1px solid #d9e2ec;
                border-radius: 8px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.value_label = QLabel("-")
        self.value_label.setStyleSheet("font-size: 24px; font-weight: 700; color: #0f172a;")
        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: #475569; font-size: 12px;")
        self.meta_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.meta_label)
        layout.addStretch(1)

    def update_content(self, title: str, value: str, meta: str = ""):
        self.title_label.setText(title)
        self.value_label.setText(value)
        self.meta_label.setText(meta)


class FigureCard(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 14, 12, 12)
        self.canvas: FigureCanvasQTAgg | None = None

    def set_figure(self, figure):
        if self.canvas is not None:
            self.layout().removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.figure.clf()

        canvas = FigureCanvasQTAgg(figure)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        figure_height = int(figure.get_size_inches()[1] * figure.dpi) + 12
        canvas.setMinimumHeight(max(320, figure_height))
        self.layout().addWidget(canvas)
        canvas.draw()
        self.canvas = canvas


class TableView(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setWordWrap(False)

    def populate(self, dataframe):
        if dataframe is None:
            self.clear()
            self.setRowCount(0)
            self.setColumnCount(0)
            return

        if isinstance(dataframe, list):
            dataframe = pd.DataFrame(dataframe)
        elif isinstance(dataframe, dict):
            dataframe = pd.DataFrame([dataframe])

        dataframe = dataframe.fillna("")
        self.setColumnCount(len(dataframe.columns))
        self.setRowCount(len(dataframe.index))
        self.setHorizontalHeaderLabels([str(column) for column in dataframe.columns])

        for row_idx, row in enumerate(dataframe.itertuples(index=False, name=None)):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(f"{value:.2f}" if isinstance(value, float) else str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_idx, col_idx, item)

        self.resizeColumnsToContents()
        if self.columnCount() > 0:
            self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)


class DesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME_EN)
        self.resize(1760, 1020)
        self.setMinimumSize(1520, 900)

        self.settings = AppSettings.load()
        self.current_artifacts = None

        self.file_path_input = QLineEdit()
        self.recent_files_combo = QComboBox()
        self.template_combo = QComboBox()
        self.preset_combo = QComboBox()
        self.sample_radio = QRadioButton("使用示例数据")
        self.upload_radio = QRadioButton("选择本地文件")
        self.status_label = QLabel("就绪")
        self.status_hint_label = QLabel("尚未开始分析。")
        self.recommended_label = QLabel("-")
        self.excel_path_label = QLabel("-")
        self.pdf_path_label = QLabel("-")
        self.param_inputs: dict[str, QLineEdit] = {}
        self.summary_cards: list[CardWidget] = []
        self.decision_cards: list[CardWidget] = []

        self.run_button: QPushButton | None = None
        self.pdf_button: QPushButton | None = None
        self.output_button: QPushButton | None = None
        self.load_template_button: QPushButton | None = None
        self.save_template_button: QPushButton | None = None
        self._preset_sync_enabled = True

        self.zone_summary_table = TableView()
        self.metrics_table = TableView()
        self.differences_table = TableView()
        self.equal_table = TableView()
        self.aligned_table = TableView()
        self.equal_points_table = TableView()
        self.aligned_points_table = TableView()
        self.config_table = TableView()

        self.temperature_card = FigureCard("温度与分区对比")
        self.layout_card = FigureCard("模块布局")
        self.metrics_card = FigureCard("归一化指标对比")
        self.radar_card = FigureCard("质量雷达图")

        self._build_window()
        self._refresh_recent_files()
        self._refresh_templates()
        self._refresh_presets()
        self._load_defaults()

    def _build_window(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        sidebar = self._build_sidebar()
        content = self._build_content()
        sidebar.setFixedWidth(520)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)

    def _build_sidebar(self):
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 8px; }")
        panel.setMinimumWidth(480)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 36, 20)
        layout.setSpacing(14)

        brand = QLabel(APP_NAME_EN)
        brand.setStyleSheet("color: #64748b; font-size: 12px;")
        title = QLabel(APP_NAME_ZH)
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        subtitle = QLabel(APP_DESCRIPTION_ZH)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #475569;")

        hint_box = QGroupBox("使用提示")
        hint_layout = QVBoxLayout(hint_box)
        hint_layout.addWidget(QLabel("1. 先看推荐结论和关键评分项胜出。"))
        hint_layout.addWidget(QLabel("2. 再看评价指标和方案差异摘要。"))
        hint_layout.addWidget(QLabel("3. 最后用工程明细确认落地风险。"))

        layout.addWidget(brand)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(hint_box)
        layout.addWidget(self._build_preset_box())
        layout.addWidget(self._build_source_box())
        layout.addWidget(self._build_params_box())
        layout.addWidget(self._build_template_box())
        layout.addWidget(self._build_action_box())
        layout.addWidget(self._build_status_box())
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        return scroll

    def _build_preset_box(self):
        box = QGroupBox("参数模板")
        layout = QVBoxLayout(box)
        self.preset_combo.currentIndexChanged.connect(self._handle_preset_changed)
        layout.addWidget(self.preset_combo)
        hint = QLabel("选择后立即覆盖当前参数。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #475569; font-size: 12px;")
        layout.addWidget(hint)
        return box

    def _build_source_box(self):
        box = QGroupBox("数据输入")
        layout = QVBoxLayout(box)
        self.sample_radio.setChecked(True)
        layout.addWidget(self.sample_radio)
        layout.addWidget(self.upload_radio)

        file_row = QHBoxLayout()
        browse_button = QPushButton("选择文件")
        browse_button.clicked.connect(self._pick_file)
        file_row.addWidget(self.file_path_input, 1)
        file_row.addWidget(browse_button)
        layout.addLayout(file_row)

        layout.addWidget(QLabel("最近文件"))
        self.recent_files_combo.currentTextChanged.connect(self._apply_recent_file)
        layout.addWidget(self.recent_files_combo)
        return box

    def _make_form_tab(self, fields: list[tuple[str, str]]) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        for key, label in fields:
            input_widget = self.param_inputs.get(key)
            if input_widget is None:
                input_widget = QLineEdit()
                input_widget.setMinimumWidth(0)
                input_widget.setMaximumWidth(220)
                self.param_inputs[key] = input_widget
            field_box = QFrame()
            field_layout = QVBoxLayout(field_box)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(4)

            label_widget = QLabel(label)
            label_widget.setWordWrap(True)
            label_widget.setStyleSheet("font-weight: 600; color: #334155;")
            input_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

            field_layout.addWidget(label_widget)
            field_layout.addWidget(input_widget, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(field_box)
        layout.addStretch(1)
        return page

    def _build_params_box(self):
        group = QGroupBox("分析参数")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        basic_fields = [
            ("total_length", "总长度 (mm)"),
            ("max_zones", "最大分区数"),
            ("equal_zone_count", "等距分区数"),
            ("alpha", "梯度权重 α"),
            ("module_length", "模块长度 (mm)"),
            ("module_gap", "模块间距 (mm)"),
            ("outer_edge_allow", "边缘外伸余量 (mm)"),
        ]
        advanced_fields = [
            ("sample_left_ratio", "左采样比例"),
            ("sample_mid_ratio", "中采样比例"),
            ("sample_right_ratio", "右采样比例"),
            ("fit_weight", "拟合权重"),
            ("separation_weight", "分离权重"),
            ("gradient_weight", "梯度权重"),
            ("heater_weight", "安装权重"),
            ("balance_weight", "均衡权重"),
            ("fit_decay", "拟合衰减"),
            ("heater_decay", "安装衰减"),
            ("internal_violation_penalty", "内部违规惩罚"),
            ("size_compliance_penalty", "尺寸合规惩罚"),
        ]
        tabs.addTab(self._make_form_tab(basic_fields), "基础参数")
        tabs.addTab(self._make_form_tab(advanced_fields), "专家参数")
        layout.addWidget(tabs)
        return group

    def _build_template_box(self):
        box = QGroupBox("自定义模板")
        layout = QVBoxLayout(box)
        layout.addWidget(self.template_combo)
        self.load_template_button = QPushButton("加载模板")
        self.save_template_button = QPushButton("保存当前参数")
        self.load_template_button.clicked.connect(self._load_template)
        self.save_template_button.clicked.connect(self._save_template)
        layout.addWidget(self.load_template_button)
        layout.addWidget(self.save_template_button)
        return box

    def _build_action_box(self):
        box = QGroupBox("执行")
        layout = QVBoxLayout(box)
        self.run_button = QPushButton("运行分析")
        self.run_button.setProperty("role", "primary")
        self.run_button.style().unpolish(self.run_button)
        self.run_button.style().polish(self.run_button)
        self.run_button.clicked.connect(self._run_analysis)

        self.pdf_button = QPushButton("导出 PDF 摘要")
        self.pdf_button.clicked.connect(self._export_pdf_summary)

        self.output_button = QPushButton("打开输出目录")
        self.output_button.clicked.connect(self._open_output_dir)

        layout.addWidget(self.run_button)
        layout.addWidget(self.pdf_button)
        layout.addWidget(self.output_button)
        return box

    def _build_status_box(self):
        box = QGroupBox("状态")
        layout = QVBoxLayout(box)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #0f172a;")
        self.status_hint_label.setWordWrap(True)
        self.status_hint_label.setStyleSheet("color: #475569;")
        self.recommended_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.excel_path_label.setWordWrap(True)
        self.pdf_path_label.setWordWrap(True)

        layout.addWidget(self.status_label)
        layout.addWidget(self.status_hint_label)
        layout.addWidget(QLabel("推荐方案"))
        layout.addWidget(self.recommended_label)
        layout.addWidget(QLabel("最近 Excel"))
        layout.addWidget(self.excel_path_label)
        layout.addWidget(QLabel("最近 PDF"))
        layout.addWidget(self.pdf_path_label)
        return box

    def _build_content(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        summary_cards = QWidget()
        cards_layout = QGridLayout(summary_cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)
        specs = [
            ("推荐方案", "#ffffff"),
            ("推荐把握", "#f7fffb"),
            ("等距分区得分", "#f7fbff"),
            ("模块对齐得分", "#fff7f7"),
            ("得分差值", "#f7fffb"),
            ("导出状态", "#ffffff"),
        ]
        for idx, (title, color) in enumerate(specs):
            card = CardWidget(title, color)
            self.summary_cards.append(card)
            cards_layout.addWidget(card, idx // 3, idx % 3)
        layout.addWidget(summary_cards)

        tabs = QTabWidget()
        tabs.addTab(self._build_decision_tab(), "决策总览")
        tabs.addTab(self._build_charts_tab(), "图表")
        tabs.addTab(self._build_engineering_tab(), "工程明细")
        layout.addWidget(tabs, 1)
        return content

    def _build_decision_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        overview_widget = QWidget()
        overview_layout = QHBoxLayout(overview_widget)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(12)
        for title in ("关键评分项胜出", "需重点复核项", "推荐方案分区数"):
            card = CardWidget(title, "#f8fbff")
            self.decision_cards.append(card)
            overview_layout.addWidget(card)
        top_layout.addWidget(overview_widget)

        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        config_box = QGroupBox("当前分析设置")
        config_layout = QVBoxLayout(config_box)
        self.config_table.setMinimumHeight(360)
        self.config_table.setMinimumWidth(360)
        config_layout.addWidget(self.config_table)

        metrics_box = QGroupBox("评价指标明细")
        metrics_layout = QVBoxLayout(metrics_box)
        self.metrics_table.setMinimumHeight(360)
        self.metrics_table.setMinimumWidth(480)
        metrics_layout.addWidget(self.metrics_table)

        diff_box = QGroupBox("方案差异摘要")
        diff_layout = QVBoxLayout(diff_box)
        self.differences_table.setMinimumHeight(360)
        self.differences_table.setMinimumWidth(480)
        diff_layout.addWidget(self.differences_table)

        bottom_splitter.addWidget(config_box)
        bottom_splitter.addWidget(metrics_box)
        bottom_splitter.addWidget(diff_box)
        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setStretchFactor(1, 1)
        bottom_splitter.setStretchFactor(2, 1)

        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_splitter)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([120, 760])

        layout.addWidget(splitter)
        return page

    def _build_charts_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QGridLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)
        scroll_layout.addWidget(self.temperature_card, 0, 0, 1, 2)
        scroll_layout.addWidget(self.layout_card, 1, 0, 1, 2)
        scroll_layout.addWidget(self.metrics_card, 2, 0, 1, 2)
        scroll_layout.addWidget(self.radar_card, 3, 0, 1, 2)
        scroll_layout.setColumnStretch(0, 1)
        scroll_layout.setColumnStretch(1, 1)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return page

    def _build_engineering_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()

        summary_page = QWidget()
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        self.zone_summary_table.setMinimumHeight(420)
        summary_layout.addWidget(self.zone_summary_table)
        tabs.addTab(summary_page, "分区汇总")

        zones_page = QWidget()
        zones_layout = QVBoxLayout(zones_page)
        zones_layout.setContentsMargins(0, 0, 0, 0)
        zone_splitter = QSplitter(Qt.Orientation.Horizontal)
        left_box = QGroupBox("等距分区结果")
        left_layout = QVBoxLayout(left_box)
        self.equal_table.setMinimumHeight(440)
        left_layout.addWidget(self.equal_table)
        right_box = QGroupBox("模块对齐分区结果")
        right_layout = QVBoxLayout(right_box)
        self.aligned_table.setMinimumHeight(440)
        right_layout.addWidget(self.aligned_table)
        zone_splitter.addWidget(left_box)
        zone_splitter.addWidget(right_box)
        zone_splitter.setStretchFactor(0, 1)
        zone_splitter.setStretchFactor(1, 1)
        zones_layout.addWidget(zone_splitter)
        tabs.addTab(zones_page, "分区结果")

        points_page = QWidget()
        points_layout = QVBoxLayout(points_page)
        points_layout.setContentsMargins(0, 0, 0, 0)
        points_splitter = QSplitter(Qt.Orientation.Horizontal)
        equal_points_box = QGroupBox("等距分区三点采样")
        equal_points_layout = QVBoxLayout(equal_points_box)
        self.equal_points_table.setMinimumHeight(420)
        equal_points_layout.addWidget(self.equal_points_table)
        aligned_points_box = QGroupBox("模块对齐三点采样")
        aligned_points_layout = QVBoxLayout(aligned_points_box)
        self.aligned_points_table.setMinimumHeight(420)
        aligned_points_layout.addWidget(self.aligned_points_table)
        points_splitter.addWidget(equal_points_box)
        points_splitter.addWidget(aligned_points_box)
        points_splitter.setStretchFactor(0, 1)
        points_splitter.setStretchFactor(1, 1)
        points_layout.addWidget(points_splitter)
        tabs.addTab(points_page, "采样点")

        layout.addWidget(tabs)
        return page

    def _refresh_recent_files(self):
        self.recent_files_combo.blockSignals(True)
        self.recent_files_combo.clear()
        self.recent_files_combo.addItems(self.settings.recent_files)
        self.recent_files_combo.blockSignals(False)

    def _refresh_templates(self):
        self.template_combo.clear()
        self.template_combo.addItems(sorted(self.settings.templates.keys()))

    def _refresh_presets(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for key, payload in PRESET_CONFIGS.items():
            self.preset_combo.addItem(payload["label"], key)
        self.preset_combo.blockSignals(False)

    def _load_defaults(self):
        self._apply_preset_by_key("balanced", update_combo=True)

    def _selected_source(self) -> str:
        return "upload" if self.upload_radio.isChecked() else "sample"

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择温度剖面文件",
            str(Path.cwd()),
            "数据文件 (*.csv *.xlsx *.xls);;所有文件 (*.*)",
        )
        if path:
            self.file_path_input.setText(path)
            self.upload_radio.setChecked(True)

    def _apply_recent_file(self, value: str):
        if value:
            self.file_path_input.setText(value)

    def _read_config(self) -> AnalysisConfig:
        return AnalysisConfig(
            total_length=float(self.param_inputs["total_length"].text()),
            max_zones=int(float(self.param_inputs["max_zones"].text())),
            equal_zone_count=int(float(self.param_inputs["equal_zone_count"].text())),
            alpha=float(self.param_inputs["alpha"].text()),
            module_length=float(self.param_inputs["module_length"].text()),
            module_gap=float(self.param_inputs["module_gap"].text()),
            outer_edge_allow=float(self.param_inputs["outer_edge_allow"].text()),
            sample_left_ratio=float(self.param_inputs["sample_left_ratio"].text()),
            sample_mid_ratio=float(self.param_inputs["sample_mid_ratio"].text()),
            sample_right_ratio=float(self.param_inputs["sample_right_ratio"].text()),
            fit_weight=float(self.param_inputs["fit_weight"].text()),
            separation_weight=float(self.param_inputs["separation_weight"].text()),
            gradient_weight=float(self.param_inputs["gradient_weight"].text()),
            heater_weight=float(self.param_inputs["heater_weight"].text()),
            balance_weight=float(self.param_inputs["balance_weight"].text()),
            fit_decay=float(self.param_inputs["fit_decay"].text()),
            heater_decay=float(self.param_inputs["heater_decay"].text()),
            internal_violation_penalty=float(self.param_inputs["internal_violation_penalty"].text()),
            size_compliance_penalty=float(self.param_inputs["size_compliance_penalty"].text()),
        ).validate()

    def _write_config(self, config: AnalysisConfig):
        payload = config.to_dict()
        for key, widget in self.param_inputs.items():
            widget.setText(str(payload[key]))

    def _apply_preset_by_key(self, key: str, update_combo: bool = False):
        base = AnalysisConfig().to_dict()
        base.update(PRESET_CONFIGS[key]["overrides"])
        self._write_config(AnalysisConfig(**base).validate())
        if update_combo:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(max(0, self.preset_combo.findData(key)))
            self.preset_combo.blockSignals(False)

    def _handle_preset_changed(self, *_args):
        if not self._preset_sync_enabled:
            return
        key = self.preset_combo.currentData()
        if not key:
            return
        self._apply_preset_by_key(key)
        self.status_label.setText(f"已选择模板：{PRESET_CONFIGS[key]['label']}")
        self.status_hint_label.setText("模板参数已立即生效，运行分析后会按当前参数重新计算。")

    def _save_template(self):
        try:
            name, accepted = QInputDialog.getText(self, "保存模板", "请输入模板名称：")
            if not accepted or not name.strip():
                return
            self.settings.save_template(name.strip(), self._read_config())
            self.settings.save()
            self._refresh_templates()
            self.template_combo.setCurrentText(name.strip())
            self.status_label.setText(f"模板已保存：{name.strip()}")
            self.status_hint_label.setText("你可以随时从“自定义模板”中重新加载。")
        except Exception as exc:
            QMessageBox.critical(self, "保存模板失败", str(exc))

    def _load_template(self):
        try:
            name = self.template_combo.currentText()
            if not name:
                raise ValueError("请先选择模板。")
            self._write_config(self.settings.load_template(name))
            self.status_label.setText(f"模板已加载：{name}")
            self.status_hint_label.setText("参数已恢复为该模板内容。")
        except Exception as exc:
            QMessageBox.critical(self, "加载模板失败", str(exc))

    def _set_busy_state(self, busy: bool, title: str, hint: str):
        self.status_label.setText(title)
        self.status_hint_label.setText(hint)
        self.status_label.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #2563eb;" if busy else "font-size: 14px; font-weight: 700; color: #0f172a;"
        )
        for widget in (
            self.run_button,
            self.pdf_button,
            self.output_button,
            self.load_template_button,
            self.save_template_button,
            self.preset_combo,
            self.template_combo,
            self.file_path_input,
            self.recent_files_combo,
        ):
            if widget is not None:
                widget.setEnabled(not busy)
        if self.run_button is not None:
            self.run_button.setText("分析中..." if busy else "运行分析")
        if busy:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def _update_summary_cards(self, artifacts):
        cards = artifacts.summary_cards
        self.summary_cards[0].update_content(cards[0]["label"], cards[0]["value"], "综合得分更高的方案")
        self.summary_cards[1].update_content(cards[1]["label"], cards[1]["value"], "基于得分差距自动判断")
        self.summary_cards[2].update_content(
            cards[2]["label"],
            cards[2]["value"],
            f"模块数 {artifacts.result.equal_metrics.total_modules} | 安装误差 {artifacts.result.equal_metrics.heater_mismatch:.2f}",
        )
        self.summary_cards[3].update_content(
            cards[3]["label"],
            cards[3]["value"],
            f"模块数 {artifacts.result.aligned_metrics.total_modules} | 安装误差 {artifacts.result.aligned_metrics.heater_mismatch:.2f}",
        )
        self.summary_cards[4].update_content(cards[4]["label"], cards[4]["value"], "两方案综合得分差")
        self.summary_cards[5].update_content("导出状态", "Excel 已生成", str(artifacts.export_path))

    def _update_decision_cards(self, artifacts):
        for card, payload in zip(self.decision_cards, build_decision_overview(artifacts.result)):
            card.update_content(payload["label"], payload["value"], payload.get("meta", ""))

    def _update_tables(self, artifacts):
        self.zone_summary_table.populate(artifacts.zone_summary)
        self.metrics_table.populate(artifacts.frames.metrics)
        self.differences_table.populate(artifacts.frames.differences)
        self.equal_table.populate(artifacts.frames.equal_zones)
        self.aligned_table.populate(artifacts.frames.aligned_zones)
        self.equal_points_table.populate(artifacts.frames.equal_points)
        self.aligned_points_table.populate(artifacts.frames.aligned_points)
        self.config_table.populate(build_config_snapshot(artifacts.result))

    def _update_charts(self, artifacts):
        result = artifacts.result
        self.temperature_card.set_figure(
            build_temperature_comparison_matplotlib(result.profile_df, result.equal_zones, result.aligned_zones)
        )
        self.layout_card.set_figure(build_module_layout_matplotlib(result.equal_zones, result.aligned_zones))
        self.metrics_card.set_figure(build_metrics_bar_matplotlib(result.equal_metrics, result.aligned_metrics))
        self.radar_card.set_figure(build_metrics_radar_matplotlib(result.equal_metrics, result.aligned_metrics))

    def _run_analysis(self):
        try:
            self._set_busy_state(True, "分析进行中", "正在计算分区、刷新图表和表格，请稍候。")
            QApplication.processEvents()

            artifacts = run_analysis_pipeline(
                config=self._read_config(),
                source=self._selected_source(),
                file_path=self.file_path_input.text().strip() or None,
            )
            self.current_artifacts = artifacts

            if self._selected_source() == "upload" and self.file_path_input.text().strip():
                self.settings.add_recent_file(self.file_path_input.text().strip())
                self.settings.save()
                self._refresh_recent_files()

            self.recommended_label.setText(artifacts.summary_cards[0]["value"])
            self.excel_path_label.setText(str(artifacts.export_path))
            self._update_summary_cards(artifacts)
            self._update_decision_cards(artifacts)
            self._update_tables(artifacts)
            self._update_charts(artifacts)
            self._set_busy_state(False, "分析完成", "结果、图表和导出文件已更新。")
            QMessageBox.information(
                self,
                "分析完成",
                f"分析已完成。\n\n推荐方案：{artifacts.summary_cards[0]['value']}\n结果、图表和导出文件已更新。",
            )
        except Exception as exc:
            self._set_busy_state(False, "执行失败", "请检查输入参数、文件格式或错误提示后重试。")
            QMessageBox.critical(self, "分析失败", str(exc))

    def _export_pdf_summary(self):
        try:
            if not self.current_artifacts:
                raise ValueError("请先运行一次分析。")
            default_name = f"heater_zoning_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "导出 PDF 摘要",
                str(Path("outputs").resolve() / default_name),
                "PDF 文件 (*.pdf)",
            )
            if not path:
                return
            export_path = export_summary_pdf(self.current_artifacts.result, Path(path))
            self.pdf_path_label.setText(str(export_path))
            self.status_label.setText("PDF 摘要导出完成")
            self.status_hint_label.setText("可直接发送给需要查看简版结论的人。")
        except Exception as exc:
            QMessageBox.critical(self, "导出 PDF 失败", str(exc))

    def _open_output_dir(self):
        output_dir = Path("outputs").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(output_dir)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir)))


def launch():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    window = DesktopApp()
    window.show()
    window._run_analysis()
    app.exec()
