"""CivilFEM 本地 PySide6 工程控制台。

桌面入口只负责界面和线程调度，CAD、网格、CalculiX、云图、报告仍复用 civilfem 后端。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable

try:
    from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
    from PySide6.QtGui import QColor, QFont, QPixmap
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout,
        QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
        QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
        QProgressBar,
    )
    QT_AVAILABLE = True
except ImportError as _qt_error:  # pragma: no cover - exercised on machines without Qt
    QT_AVAILABLE = False
    _QT_ERROR = _qt_error

if QT_AVAILABLE:
    from civilfem.api_client import ApiClientError, explain_result
    from civilfem.api_config import load_api_config
    from civilfem.mcp_api import build_mesh, generate_report, run_fem_analysis
    from civilfem.security import configured_project_root
    from civilfem.visualization import render_cad_preview, render_mesh
    from civilfem.workflow import inspect_input
    from gui import build_cad_model, inspect_uploaded_model, save_upload


COLORS = {
    "bg": "#08111f", "panel": "#0d1928", "panel2": "#101f31", "line": "#293d55",
    "text": "#d8e6f7", "muted": "#8ea4bf", "blue": "#218bff", "green": "#69d66d",
    "red": "#ff625f", "yellow": "#ffc72c",
}


def _safe_error(error: Exception | str) -> str:
    """返回可展示错误，不输出 API URL、Key 或完整命令日志。"""
    text = str(error)
    for token in ("sk-", "Bearer "):
        if token in text:
            return "外部服务调用失败（凭据已隐藏）"
    return text[:240]


if QT_AVAILABLE:
    class TaskWorker(QObject):
        finished = Signal(object)
        failed = Signal(str)
        progress = Signal(str, int)

        def __init__(self, fn: Callable[[], dict[str, Any]]):
            super().__init__()
            self.fn = fn

        @Slot()
        def run(self) -> None:
            try:
                self.progress.emit("处理中", 45)
                result = self.fn()
                self.finished.emit(result)
            except Exception as error:  # noqa: BLE001 - worker boundary
                self.failed.emit(_safe_error(error))


    class MetricCard(QFrame):
        def __init__(self, title: str, value: str = "—", unit: str = "", accent: str = "text"):
            super().__init__()
            self.setObjectName("metricCard")
            layout = QVBoxLayout(self)
            layout.setContentsMargins(14, 12, 14, 12)
            title_label = QLabel(title)
            title_label.setObjectName("metricTitle")
            row = QHBoxLayout()
            self.value_label = QLabel(value)
            self.value_label.setObjectName(f"metricValue_{accent}")
            unit_label = QLabel(unit)
            unit_label.setObjectName("metricUnit")
            row.addWidget(self.value_label)
            row.addWidget(unit_label, 0, Qt.AlignmentFlag.AlignBottom)
            row.addStretch()
            layout.addWidget(title_label)
            layout.addLayout(row)

        def set_value(self, value: str) -> None:
            self.value_label.setText(value)


    class StepItem(QFrame):
        clicked = Signal()

        def __init__(self, title: str, subtitle: str, icon: str):
            super().__init__()
            self.setObjectName("stepItem")
            self.title = title
            self.subtitle = subtitle
            layout = QHBoxLayout(self)
            layout.setContentsMargins(20, 16, 12, 16)
            icon_label = QLabel(icon)
            icon_label.setObjectName("stepIcon")
            icon_label.setFixedWidth(34)
            body = QVBoxLayout()
            title_label = QLabel(title)
            title_label.setObjectName("stepTitle")
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("stepSubtitle")
            body.addWidget(title_label)
            body.addWidget(subtitle_label)
            layout.addWidget(icon_label)
            layout.addLayout(body)
            layout.addStretch()

        def mousePressEvent(self, event):  # noqa: N802
            self.clicked.emit()
            super().mousePressEvent(event)


    class DesktopWindow(QMainWindow):
        def __init__(self, project_root: str | Path | None = None):
            super().__init__()
            self.project_root = configured_project_root(project_root or os.getcwd())
            self.current_path: Path | None = None
            self.current_hash: str | None = None
            self.inspection: dict[str, Any] | None = None
            self.model: dict[str, Any] | None = None
            self.mesh: dict[str, Any] | None = None
            self.run: dict[str, Any] | None = None
            self.result: dict[str, Any] = {}
            self.image_path: str | None = None
            self._thread: QThread | None = None
            self._worker: TaskWorker | None = None
            self.setWindowTitle("CivilFEM · 本地工程控制台")
            self.setMinimumSize(1500, 860)
            self.resize(2048, 1152)
            self.setStyleSheet(self._qss())
            self._build_ui()

        def _qss(self) -> str:
            return f"""
            QMainWindow, QWidget {{ background: {COLORS['bg']}; color: {COLORS['text']}; font-family: 'Segoe UI','Microsoft YaHei'; }}
            QFrame#topBar, QFrame#leftPanel, QFrame#rightPanel, QFrame#bottomBar, QFrame#metricCard {{ background: {COLORS['panel']}; border: 1px solid {COLORS['line']}; }}
            QFrame#topBar {{ border-top: 0; padding: 4px; }}
            QFrame#leftPanel, QFrame#rightPanel {{ border-top: 0; border-bottom: 0; }}
            QFrame#metricCard {{ border-radius: 4px; }}
            QLabel#brand {{ font-size: 24px; font-weight: 700; color: #f1f6ff; }}
            QLabel#topKey {{ color: {COLORS['muted']}; font-size: 14px; }}
            QLabel#topValue {{ color: {COLORS['blue']}; font-size: 14px; font-weight: 600; }}
            QLabel#sectionTitle {{ font-size: 16px; font-weight: 600; color: #dcecff; }}
            QLabel#metricTitle, QLabel#metricUnit, QLabel#stepSubtitle {{ color: {COLORS['muted']}; font-size: 12px; }}
            QLabel#metricValue_text, QLabel#metricValue_blue, QLabel#metricValue_green, QLabel#metricValue_red {{ font-size: 23px; font-weight: 700; }}
            QLabel#metricValue_blue {{ color: {COLORS['blue']}; }} QLabel#metricValue_green {{ color: {COLORS['green']}; }} QLabel#metricValue_red {{ color: {COLORS['red']}; }}
            QLabel#stepTitle {{ font-size: 15px; font-weight: 600; }} QLabel#stepIcon {{ font-size: 24px; color: #b9cce4; }}
            QFrame#stepItem {{ border-left: 3px solid transparent; }} QFrame#stepItem:hover {{ background: {COLORS['panel2']}; border-left-color: {COLORS['blue']}; }}
            QLabel#viewport {{ background: #091522; border: 1px solid {COLORS['line']}; color: {COLORS['muted']}; font-size: 16px; }}
            QPushButton {{ background: #122b48; border: 1px solid #2a527d; border-radius: 3px; padding: 9px 13px; color: #e6f1ff; font-weight: 600; }}
            QPushButton:hover {{ background: #1a4f87; }} QPushButton#primary {{ background: {COLORS['blue']}; border-color: #4ca2ff; }}
            QPushButton#danger {{ background: #4b2028; border-color: #a84852; }}
            QLineEdit, QDoubleSpinBox, QComboBox {{ background: #0a1624; border: 1px solid {COLORS['line']}; padding: 7px; color: {COLORS['text']}; }}
            QScrollArea {{ border: 0; }} QSplitter::handle {{ background: {COLORS['line']}; }}
            QProgressBar {{ border: 1px solid {COLORS['line']}; background: #091522; height: 5px; }} QProgressBar::chunk {{ background: {COLORS['blue']}; }}
            """

        def _label(self, text: str, object_name: str = "") -> QLabel:
            label = QLabel(text)
            if object_name:
                label.setObjectName(object_name)
            return label

        def _build_ui(self) -> None:
            root = QWidget()
            outer = QVBoxLayout(root)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            outer.addWidget(self._build_top_bar())
            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.setChildrenCollapsible(False)
            splitter.addWidget(self._build_left_panel())
            splitter.addWidget(self._build_viewport())
            splitter.addWidget(self._build_right_panel())
            splitter.setSizes([285, 1200, 405])
            outer.addWidget(splitter, 1)
            outer.addWidget(self._build_bottom_bar())
            self.setCentralWidget(root)

        def _build_top_bar(self) -> QFrame:
            frame = QFrame(); frame.setObjectName("topBar"); frame.setFixedHeight(82)
            row = QHBoxLayout(frame); row.setContentsMargins(28, 0, 24, 0); row.setSpacing(26)
            row.addWidget(self._label("⬡  CivilFEM", "brand"))
            row.addWidget(self._label("│", "topKey"))
            self.project_label = self._label("项目：未选择", "topValue"); row.addWidget(self.project_label)
            row.addWidget(self._label("│  模型：—", "topValue"))
            row.addStretch()
            self.solver_label = self._label("求解状态：● 未开始", "topKey"); row.addWidget(self.solver_label)
            self.mesh_quality = self._label("网格质量：—", "topKey"); row.addWidget(self.mesh_quality)
            row.addWidget(self._label("运行时间：—", "topKey"))
            return frame

        def _build_left_panel(self) -> QFrame:
            frame = QFrame(); frame.setObjectName("leftPanel"); frame.setMinimumWidth(250); frame.setMaximumWidth(330)
            layout = QVBoxLayout(frame); layout.setContentsMargins(0, 18, 0, 12); layout.setSpacing(2)
            self.steps: dict[str, StepItem] = {}
            for key, title, subtitle, icon in (("cad", "CAD", "导入图纸", "▱"), ("model", "模型", "定义属性", "◇"), ("mesh", "网格", "生成网格", "▦"), ("solve", "求解", "运行分析", "◉"), ("report", "报告", "生成报告", "▤")):
                item = StepItem(title, subtitle, icon); self.steps[key] = item; layout.addWidget(item)
            layout.addStretch()
            tools = self._label("◈   ◉   ⛶   ▣   ⌁", "topKey"); tools.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(tools)
            return frame

        def _build_viewport(self) -> QWidget:
            frame = QFrame(); layout = QVBoxLayout(frame); layout.setContentsMargins(0, 0, 0, 0)
            head = QHBoxLayout(); head.setContentsMargins(28, 22, 28, 6)
            head.addWidget(self._label("von Mises 应力云图", "sectionTitle")); head.addStretch()
            self.viewport_status = self._label("等待导入图纸", "topKey"); head.addWidget(self.viewport_status)
            layout.addLayout(head)
            self.viewport = QLabel("导入 JSON 或 DXF 图纸\n\n主视图区将显示 CAD 预览、网格或应力云图")
            self.viewport.setObjectName("viewport"); self.viewport.setAlignment(Qt.AlignmentFlag.AlignCenter); self.viewport.setMinimumSize(700, 500); self.viewport.setScaledContents(False)
            layout.addWidget(self.viewport, 1)
            controls = QHBoxLayout(); controls.setContentsMargins(28, 8, 28, 14)
            self.choose_button = QPushButton("选择图纸"); self.choose_button.clicked.connect(self.choose_file)
            self.map_button = QPushButton("显式映射 H 型钢梁"); self.map_button.clicked.connect(self.map_cad); self.map_button.setEnabled(False)
            self.mesh_button = QPushButton("生成网格"); self.mesh_button.clicked.connect(self.start_mesh); self.mesh_button.setEnabled(False)
            self.solve_button = QPushButton("运行三维 FEM"); self.solve_button.setObjectName("primary"); self.solve_button.clicked.connect(self.start_solve); self.solve_button.setEnabled(False)
            for button in (self.choose_button, self.map_button, self.mesh_button, self.solve_button): controls.addWidget(button)
            controls.addStretch(); layout.addLayout(controls)
            return frame

        def _build_right_panel(self) -> QWidget:
            frame = QFrame(); frame.setObjectName("rightPanel"); frame.setMinimumWidth(365); frame.setMaximumWidth(500)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(frame)
            layout = QVBoxLayout(frame); layout.setContentsMargins(24, 28, 22, 18); layout.setSpacing(12)
            layout.addWidget(self._label("结果摘要", "sectionTitle"))
            self.stress_card = MetricCard("最大 von Mises 应力", "—", "MPa", "red"); layout.addWidget(self.stress_card)
            self.displacement_card = MetricCard("最大位移", "—", "mm", "blue"); layout.addWidget(self.displacement_card)
            layout.addWidget(self._label("网格信息", "sectionTitle"))
            self.mesh_info = self._label("单元数：—\n节点数：—\n单元类型：—\n平均质量：—", "topKey"); layout.addWidget(self.mesh_info)
            layout.addWidget(self._label("求解信息", "sectionTitle"))
            self.solve_info = self._label("求解器：CalculiX\n分析类型：静力结构\n收敛状态：—\nCPU 时间：—", "topKey"); layout.addWidget(self.solve_info)
            self.export_button = QPushButton("导出专业报告（Markdown）"); self.export_button.clicked.connect(lambda: self.export_report("markdown")); self.export_button.setEnabled(False); layout.addWidget(self.export_button)
            html_button = QPushButton("导出 HTML 报告"); html_button.clicked.connect(lambda: self.export_report("html")); html_button.setEnabled(False); self.html_button = html_button; layout.addWidget(html_button)
            self.ai_button = QPushButton("AI 结果分析（可选）"); self.ai_button.clicked.connect(self.ai_analysis); self.ai_button.setEnabled(False); layout.addWidget(self.ai_button)
            layout.addStretch(); return scroll

        def _build_bottom_bar(self) -> QFrame:
            frame = QFrame(); frame.setObjectName("bottomBar"); frame.setFixedHeight(96)
            layout = QVBoxLayout(frame); layout.setContentsMargins(28, 10, 28, 12)
            self.progress = self._label("作业 ID：—       模型检查  ·  网格生成  ·  求解  ·  后处理  ·  完成", "topKey"); layout.addWidget(self.progress)
            self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 100); self.progress_bar.setValue(0); layout.addWidget(self.progress_bar)
            return frame

        def _set_busy(self, text: str, value: int = 15) -> None:
            self.viewport_status.setText(text); self.progress.setText(text); self.progress_bar.setValue(value)

        def _run_worker(self, fn: Callable[[], dict[str, Any]], done: Callable[[dict[str, Any]], None]) -> None:
            if self._thread and self._thread.isRunning(): return
            self._thread = QThread(self); self._worker = TaskWorker(fn); self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.run); self._worker.progress.connect(lambda text, value: self._set_busy(text, value))
            self._worker.finished.connect(done); self._worker.failed.connect(self._show_error)
            self._worker.finished.connect(self._thread.quit); self._worker.failed.connect(self._thread.quit)
            self._thread.finished.connect(self._worker.deleteLater); self._thread.finished.connect(self._thread.deleteLater); self._thread.start()

        def choose_file(self) -> None:
            path, _ = QFileDialog.getOpenFileName(self, "选择 CAD 或模型文件", str(self.project_root), "工程文件 (*.json *.dxf *.ifc *.step *.stp *.fcstd)")
            if not path: return
            source = Path(path)
            try:
                target = save_upload(source.read_bytes(), source.name, self.project_root)
                self.current_path = target
            except Exception as error:
                self._show_error(_safe_error(error)); return
            self._set_busy("正在检查图纸", 10); self._reset_for_new_input()
            self._run_worker(lambda: inspect_input(str(self.current_path), str(self.project_root)), self._input_ready)

        def _reset_for_new_input(self) -> None:
            self.model = self.mesh = self.run = None; self.result = {}; self.map_button.setEnabled(False); self.mesh_button.setEnabled(False); self.solve_button.setEnabled(False); self.export_button.setEnabled(False); self.html_button.setEnabled(False); self.ai_button.setEnabled(False)

        def _input_ready(self, inspection: dict[str, Any]) -> None:
            self.inspection = inspection; self.current_hash = inspection.get("sha256")
            if inspection.get("status") != "inspected": self._show_error("图纸检查失败：" + ", ".join(inspection.get("issues", []))); return
            self.project_label.setText(f"项目：{self.current_path.stem if self.current_path else '未选择'}")
            suffix = self.current_path.suffix.lower() if self.current_path else ""
            if suffix == ".json":
                result = inspect_uploaded_model(self.current_path, self.project_root)
                self.model = result.get("model") if result.get("status") == "valid" else None
                self.viewport_status.setText("模型已检查" if self.model else "模型待确认")
                if self.model: self._model_ready()
            elif suffix == ".dxf":
                preview = render_cad_preview(self.current_path)
                self._show_image(preview.get("image")); self.viewport_status.setText("CAD 几何预览 · 未自动映射钢梁"); self.map_button.setEnabled(True)
            else:
                self.viewport_status.setText(f"已检查 {suffix[1:].upper()}，等待后端适配")
            self.progress_bar.setValue(25)

        def _model_ready(self) -> None:
            self.map_button.setEnabled(False); self.mesh_button.setEnabled(True); self.solve_button.setEnabled(True); self.ai_button.setEnabled(False); self.steps["model"].setStyleSheet("border-left: 3px solid #218bff; background:#101f31;")

        def map_cad(self) -> None:
            if not self.inspection: return
            dialog = QWidget(); dialog.setWindowTitle("显式 H 型钢梁映射")
            layout = QGridLayout(dialog); fields: dict[str, QWidget] = {}
            defaults = {"h": 300, "b": 300, "tw": 10, "tf": 15, "length": 6000, "N": 0, "Mx": 0, "V": 0}
            for row, (name, value) in enumerate(defaults.items()):
                layout.addWidget(QLabel(name), row, 0); spin = QDoubleSpinBox(); spin.setRange(-1e9, 1e9); spin.setValue(value); fields[name] = spin; layout.addWidget(spin, row, 1)
            layout.addWidget(QLabel("steel"), len(defaults), 0); steel = QComboBox(); steel.addItems(["Q355", "Q235", "S355"]); fields["steel"] = steel; layout.addWidget(steel, len(defaults), 1)
            ok = QPushButton("确认映射"); ok.setObjectName("primary"); layout.addWidget(ok, len(defaults) + 1, 0, 1, 2); ok.setStyleSheet(self._qss()); dialog.setStyleSheet(self._qss()); dialog.setMinimumWidth(330); dialog.show()
            ok.clicked.connect(lambda: (self._complete_mapping({key: (value.currentText() if isinstance(value, QComboBox) else value.value()) for key, value in fields.items()}), dialog.close()))
            self._mapping_dialog = dialog

        def _complete_mapping(self, fields: dict[str, QWidget]) -> None:
            if not fields: return
            params = {key: (widget if isinstance(widget, (str, float, int)) else (widget.currentText() if isinstance(widget, QComboBox) else widget.value())) for key, widget in fields.items()}
            mapped = build_cad_model(self.inspection or {}, params)
            if mapped.get("status") != "valid": self._show_error(mapped.get("error", "钢梁映射失败")); return
            self.model = mapped.get("model"); self.viewport_status.setText("已显式映射 H 型钢梁"); self._model_ready()

        def start_mesh(self) -> None:
            if not self.model: return
            self._set_busy("正在生成 Gmsh 网格", 35); self._run_worker(lambda: build_mesh(self.model, str(self.project_root), 100.0), self._mesh_ready)

        def _mesh_ready(self, result: dict[str, Any]) -> None:
            self.mesh = result
            if result.get("status") != "completed": self._show_error(result.get("reason") or result.get("error") or "网格生成失败"); return
            preview = render_mesh(result["mesh"]); self._show_image(preview.get("image")); self.viewport_status.setText("网格已生成"); self.progress_bar.setValue(55); self.solve_button.setEnabled(True)

        def start_solve(self) -> None:
            if not self.model: return
            mesh_path = (self.mesh or {}).get("mesh")
            self._set_busy("CalculiX 求解中", 65); started = time.perf_counter()
            self._run_worker(lambda: run_fem_analysis(self.model, str(self.project_root), mesh_path, 100.0), lambda result: self._solve_ready(result, started))

        def _solve_ready(self, run: dict[str, Any], started: float) -> None:
            self.run = run; self.result = run.get("result") or {}
            if run.get("status") != "completed": self._show_error(run.get("error") or "CalculiX 求解失败"); return
            cloud = (self.result.get("stress_cloud") or {}).get("image")
            if cloud: self._show_image(cloud)
            self.stress_card.set_value(f"{float(self.result.get('max_von_mises', 0.0)):.2f}"); self.displacement_card.set_value(f"{float(self.result.get('max_displacement', 0.0)):.3f}")
            self.mesh_info.setText(f"单元数：{(self.result.get('stress_cloud') or {}).get('cell_count', '—')}\n节点数：{(self.result.get('stress_cloud') or {}).get('point_count', '—')}\n单元类型：{(self.result.get('quality') or {}).get('mesh_element_type', 'C3D4')}\n网格尺寸：{(self.result.get('quality') or {}).get('mesh_size_mm', '—')} mm")
            self.solve_info.setText(f"求解器：CalculiX\n分析类型：静力结构\n收敛状态：已完成\nCPU 时间：{time.perf_counter()-started:.1f} s")
            self.solver_label.setText("求解状态：● 已完成"); self.solver_label.setStyleSheet(f"color:{COLORS['green']}"); self.mesh_quality.setText("网格质量：已生成"); self.viewport_status.setText("应力云图 · von Mises (MPa)"); self.progress_bar.setValue(100); self.progress.setText(f"作业 ID：{run.get('run_id', '—')}       模型检查 ✓  网格生成 ✓  求解 ✓  后处理 ✓  完成 ✓"); self.export_button.setEnabled(True); self.html_button.setEnabled(True); self.ai_button.setEnabled(True)

        def export_report(self, fmt: str) -> None:
            if not self.run: return
            report = generate_report(self.run["run_id"], str(self.project_root), fmt=fmt)
            if report.get("report"): QMessageBox.information(self, "报告已生成", f"已生成 {fmt.upper()} 报告：\n{report['report']}")
            else: self._show_error(report.get("error", "报告生成失败"))

        def ai_analysis(self) -> None:
            try:
                text = explain_result(load_api_config(), {"max_von_mises": self.result.get("max_von_mises"), "max_displacement": self.result.get("max_displacement"), "quality": self.result.get("quality")})
            except ApiClientError as error:
                self._show_error(_safe_error(error)); return
            QMessageBox.information(self, "AI 工程辅助分析", text)

        def _show_image(self, path: str | None) -> None:
            if not path or not Path(path).is_file(): return
            pixmap = QPixmap(path)
            self.image_path = path
            self.viewport.setPixmap(pixmap.scaled(self.viewport.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.viewport.setText("")

        def resizeEvent(self, event):  # noqa: N802
            super().resizeEvent(event)
            if self.image_path: self._show_image(self.image_path)

        def _show_error(self, message: str) -> None:
            self.viewport_status.setText("操作失败"); self.progress.setText("操作失败：" + _safe_error(message)); QMessageBox.warning(self, "CivilFEM", _safe_error(message))


def main(argv: list[str] | None = None) -> int:
    if not QT_AVAILABLE:
        raise RuntimeError('PySide6 未安装。运行：python -m pip install -e ".[desktop]"') from _QT_ERROR
    app = QApplication(argv or sys.argv)
    app.setApplicationName("CivilFEM")
    window = DesktopWindow()
    window.show()
    return app.exec()




if __name__ == "__main__":
    raise SystemExit(main())
