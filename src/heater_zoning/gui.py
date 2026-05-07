from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
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
        self.value_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #0f172a;")
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

        dataframe = dataframe.fillna("")
        self.setColumnCount(len(dataframe.columns))
        self.setRowCount(len(dataframe.index))
        self.setHorizontalHeaderLabels([str(column) for column in dataframe.columns])

        for row_idx, row in enumerate(dataframe.itertuples(index=False, name=None)):
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(row_idx, col_idx, item)

        self.resizeColumnsToContents()
        header = self.horizontalHeader()
        if self.columnCount() > 0:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)


class DesktopApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Heater Zoning Optimizer")
        self.resize(1600, 980)
        self.setMinimumSize(1380, 860)

        self.settings = AppSettings.load()
        self.current_artifacts = None

        self.source_group = QButtonGroup(self)
        self.file_path_input = QLineEdit()
        self.recent_files_combo = QComboBox()
        self.template_combo = QComboBox()
        self.status_label = QLabel("就绪")
        self.recommended_label = QLabel("-")
        self.excel_path_label = QLabel("-")
        self.pdf_path_label = QLabel("-")
        self.param_inputs: dict[str, QLineEdit] = {}
        self.summary_cards: list[CardWidget] = []

        self.summary_table = TableView()
        self.metrics_table = TableView()
        self.equal_table = TableView()
        self.aligned_table = TableView()
        self.equal_points_table = TableView()
        self.aligned_points_table = TableView()

        self.temperature_card = FigureCard("温度与分区对比")
        self.layout_card = FigureCard("模块排布图")
        self.metrics_card = FigureCard("指标对比")
        self.radar_card = FigureCard("雷达图")

        self._build_window()
        self._refresh_recent_files()
        self._refresh_templates()
        self._load_defaults()

    def _build_window(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        sidebar = self._build_sidebar()
        content = self._build_content()
        sidebar.setFixedWidth(376)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)

        export_action = QAction("打开输出目录", self)
        export_action.triggered.connect(self._open_output_dir)
        self.addAction(export_action)

    def _build_sidebar(self):
        panel = QFrame()
        panel.setStyleSheet("QFrame { background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 8px; }")
        panel.setMinimumWidth(344)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        brand = QLabel("Heater Zoning Optimizer")
        brand.setStyleSheet("color: #64748b; font-size: 12px;")
        title = QLabel("加热分区分析台")
        title.setStyleSheet("font-size: 28px; font-weight: 700;")
        subtitle = QLabel("加载温度剖面，比较等距分区与模块对齐方案，输出图表、Excel 和 PDF。")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #475569; line-height: 1.45;")

        layout.addWidget(brand)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_source_box())
        layout.addWidget(self._build_params_box())
        layout.addWidget(self._build_template_box())
        layout.addWidget(self._build_action_box())
        layout.addWidget(self._build_status_box())
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(panel)
        return scroll

    def _build_source_box(self):
        box = QGroupBox("数据输入")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        sample_radio = QRadioButton("使用示例数据")
        upload_radio = QRadioButton("选择本地文件")
        sample_radio.setChecked(True)
        self.source_group.addButton(sample_radio)
        self.source_group.addButton(upload_radio)
        self.source_group.setId(sample_radio, 0)
        self.source_group.setId(upload_radio, 1)

        layout.addWidget(sample_radio)
        layout.addWidget(upload_radio)

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

    def _build_params_box(self):
        box = QGroupBox("分析参数")
        form = QFormLayout(box)
        form.setContentsMargins(14, 18, 14, 14)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        fields = [
            ("total_length", "总长度 (mm)"),
            ("max_zones", "最大分区数"),
            ("equal_zone_count", "等距分区数"),
            ("alpha", "梯度权重 alpha"),
            ("module_length", "模块长度 (mm)"),
            ("module_gap", "模块间距 (mm)"),
            ("outer_edge_allow", "边缘外伸余量 (mm)"),
            ("sample_left_ratio", "左点比例"),
            ("sample_mid_ratio", "中点比例"),
            ("sample_right_ratio", "右点比例"),
            ("fit_weight", "拟合权重"),
            ("separation_weight", "分离权重"),
            ("gradient_weight", "梯度权重"),
            ("heater_weight", "安装匹配权重"),
            ("balance_weight", "均衡权重"),
            ("fit_decay", "拟合衰减"),
            ("heater_decay", "安装衰减"),
            ("internal_violation_penalty", "违规惩罚"),
            ("size_compliance_penalty", "合规惩罚"),
        ]
        for key, label in fields:
            line_edit = QLineEdit()
            self.param_inputs[key] = line_edit
            form.addRow(label, line_edit)
        return box

    def _build_template_box(self):
        box = QGroupBox("参数模板")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)
        layout.addWidget(self.template_combo)

        load_button = QPushButton("加载模板")
        save_button = QPushButton("保存当前参数")
        load_button.clicked.connect(self._load_template)
        save_button.clicked.connect(self._save_template)
        layout.addWidget(load_button)
        layout.addWidget(save_button)
        return box

    def _build_action_box(self):
        box = QGroupBox("执行")
        layout = QVBoxLayout(box)
        layout.setSpacing(10)

        run_button = QPushButton("运行分析")
        run_button.setProperty("role", "primary")
        run_button.style().unpolish(run_button)
        run_button.style().polish(run_button)
        run_button.clicked.connect(self._run_analysis)

        pdf_button = QPushButton("导出 PDF 摘要")
        pdf_button.clicked.connect(self._export_pdf_summary)

        output_button = QPushButton("打开输出目录")
        output_button.clicked.connect(self._open_output_dir)

        layout.addWidget(run_button)
        layout.addWidget(pdf_button)
        layout.addWidget(output_button)
        return box

    def _build_status_box(self):
        box = QGroupBox("状态")
        layout = QVBoxLayout(box)
        layout.setSpacing(8)

        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #475569;")
        self.recommended_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.excel_path_label.setWordWrap(True)
        self.pdf_path_label.setWordWrap(True)
        self.excel_path_label.setStyleSheet("color: #475569;")
        self.pdf_path_label.setStyleSheet("color: #475569;")

        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("推荐方案"))
        layout.addWidget(self.recommended_label)
        layout.addWidget(QLabel("最近 Excel 导出"))
        layout.addWidget(self.excel_path_label)
        layout.addWidget(QLabel("最近 PDF 导出"))
        layout.addWidget(self.pdf_path_label)
        return box

    def _build_content(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        cards = QWidget()
        cards_layout = QGridLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(16)
        cards_layout.setVerticalSpacing(16)

        card_specs = [
            ("推荐方案", "#ffffff"),
            ("等距分区得分", "#f7fbff"),
            ("模块对齐得分", "#fff7f7"),
            ("导出状态", "#f7fffb"),
        ]
        for idx, (title, color) in enumerate(card_specs):
            card = CardWidget(title, color)
            self.summary_cards.append(card)
            cards_layout.addWidget(card, 0, idx)

        layout.addWidget(cards)

        tabs = QTabWidget()
        tabs.addTab(self._build_overview_tab(), "总览")
        tabs.addTab(self._build_charts_tab(), "图表")
        tabs.addTab(self._build_tables_tab(), "明细表")
        layout.addWidget(tabs, 1)
        return content

    def _build_overview_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        summary_box = QGroupBox("分区汇总")
        summary_layout = QVBoxLayout(summary_box)
        summary_layout.setContentsMargins(12, 14, 12, 12)
        summary_layout.addWidget(self.summary_table)
        layout.addWidget(summary_box, 1)
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
        scroll_layout.setHorizontalSpacing(16)
        scroll_layout.setVerticalSpacing(16)

        scroll_layout.addWidget(self.temperature_card, 0, 0, 1, 2)
        scroll_layout.addWidget(self.layout_card, 1, 0, 1, 2)
        scroll_layout.addWidget(self.metrics_card, 2, 0, 1, 2)
        scroll_layout.addWidget(self.radar_card, 3, 0, 1, 2)
        scroll_layout.setColumnStretch(0, 1)
        scroll_layout.setColumnStretch(1, 1)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return page

    def _build_tables_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        detail_tabs = QTabWidget()

        metrics_page = QWidget()
        metrics_layout = QVBoxLayout(metrics_page)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.addWidget(self.metrics_table)
        detail_tabs.addTab(metrics_page, "评价指标")

        zones_page = QWidget()
        zones_layout = QVBoxLayout(zones_page)
        zones_layout.setContentsMargins(0, 0, 0, 0)
        zone_splitter = QSplitter(Qt.Orientation.Horizontal)
        equal_box = QGroupBox("等距分区结果")
        equal_layout = QVBoxLayout(equal_box)
        equal_layout.setContentsMargins(12, 14, 12, 12)
        equal_layout.addWidget(self.equal_table)
        aligned_box = QGroupBox("模块对齐分区结果")
        aligned_layout = QVBoxLayout(aligned_box)
        aligned_layout.setContentsMargins(12, 14, 12, 12)
        aligned_layout.addWidget(self.aligned_table)
        zone_splitter.addWidget(equal_box)
        zone_splitter.addWidget(aligned_box)
        zone_splitter.setSizes([1, 1])
        zones_layout.addWidget(zone_splitter)
        detail_tabs.addTab(zones_page, "分区结果")

        points_page = QWidget()
        points_layout = QVBoxLayout(points_page)
        points_layout.setContentsMargins(0, 0, 0, 0)
        points_splitter = QSplitter(Qt.Orientation.Horizontal)
        equal_points_box = QGroupBox("等距分区三点采样")
        equal_points_layout = QVBoxLayout(equal_points_box)
        equal_points_layout.setContentsMargins(12, 14, 12, 12)
        equal_points_layout.addWidget(self.equal_points_table)
        aligned_points_box = QGroupBox("模块对齐三点采样")
        aligned_points_layout = QVBoxLayout(aligned_points_box)
        aligned_points_layout.setContentsMargins(12, 14, 12, 12)
        aligned_points_layout.addWidget(self.aligned_points_table)
        points_splitter.addWidget(equal_points_box)
        points_splitter.addWidget(aligned_points_box)
        points_splitter.setSizes([1, 1])
        points_layout.addWidget(points_splitter)
        detail_tabs.addTab(points_page, "采样点")

        layout.addWidget(detail_tabs)
        return page

    def _load_defaults(self):
        self._write_config(AnalysisConfig().validate())

    def _selected_source(self) -> str:
        return "upload" if self.source_group.checkedId() == 1 else "sample"

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择温度剖面文件",
            str(Path.cwd()),
            "数据文件 (*.csv *.xlsx *.xls);;所有文件 (*.*)",
        )
        if path:
            self.file_path_input.setText(path)
            button = self.source_group.buttons()[1]
            button.setChecked(True)

    def _apply_recent_file(self, value: str):
        if value:
            self.file_path_input.setText(value)

    def _refresh_recent_files(self):
        self.recent_files_combo.blockSignals(True)
        self.recent_files_combo.clear()
        self.recent_files_combo.addItems(self.settings.recent_files)
        self.recent_files_combo.blockSignals(False)

    def _refresh_templates(self):
        names = sorted(self.settings.templates.keys())
        self.template_combo.clear()
        self.template_combo.addItems(names)

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
        except Exception as exc:
            QMessageBox.critical(self, "保存模板失败", str(exc))

    def _load_template(self):
        try:
            name = self.template_combo.currentText()
            if not name:
                raise ValueError("请先选择模板。")
            self._write_config(self.settings.load_template(name))
            self.status_label.setText(f"模板已加载：{name}")
        except Exception as exc:
            QMessageBox.critical(self, "加载模板失败", str(exc))

    def _update_cards(self, artifacts):
        cards = artifacts.summary_cards
        if len(cards) >= 4:
            self.summary_cards[0].update_content(cards[0]["label"], cards[0]["value"], "综合得分更高的方案")
            self.summary_cards[1].update_content(
                cards[1]["label"],
                cards[1]["value"],
                f"模块数 {artifacts.result.equal_metrics.total_modules} | 安装误差 {artifacts.result.equal_metrics.heater_mismatch:.3f}",
            )
            self.summary_cards[2].update_content(
                cards[2]["label"],
                cards[2]["value"],
                f"模块数 {artifacts.result.aligned_metrics.total_modules} | 安装误差 {artifacts.result.aligned_metrics.heater_mismatch:.3f}",
            )
            self.summary_cards[3].update_content("导出状态", "Excel 已生成", str(artifacts.export_path))

    def _update_tables(self, artifacts):
        self.summary_table.populate(artifacts.zone_summary)
        self.metrics_table.populate(artifacts.frames.metrics)
        self.equal_table.populate(artifacts.frames.equal_zones)
        self.aligned_table.populate(artifacts.frames.aligned_zones)
        self.equal_points_table.populate(artifacts.frames.equal_points)
        self.aligned_points_table.populate(artifacts.frames.aligned_points)

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
            self.status_label.setText("分析中，请稍候...")
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
            self.status_label.setText("分析完成。图表、表格和导出文件已更新。")
            self._update_cards(artifacts)
            self._update_tables(artifacts)
            self._update_charts(artifacts)
        except Exception as exc:
            self.status_label.setText("执行失败")
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
            self.status_label.setText("PDF 摘要导出完成。")
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
