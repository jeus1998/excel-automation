from collections import Counter
from pathlib import Path
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListView, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QProgressDialog, QStackedWidget, QStyleFactory,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from services.amount_comparator import compare_amounts
from services.container_matcher import reconcile_containers
from services.excel_loader import load_workbook, load_sheet, load_sheet_data, load_column_values
from services.task_plan_validator import validate_plan
from services.data_normalizer import is_valid_container_number

if getattr(sys, "frozen", False):
    BACKGROUND = Path(sys._MEIPASS) / "resources" / "images" / "home_background.png"
else:
    BACKGROUND = Path(__file__).resolve().parents[1] / "resources" / "images" / "home_background.png"


class ImageBackground(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.pixmap = QPixmap(str(image_path))

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(-x, -y, scaled)
        else:
            painter.fillRect(self.rect(), QColor("#dce8e4"))
        painter.fillRect(self.rect(), QColor(17, 32, 32, 78))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Container Workbench")
        self.resize(1240, 860)
        self.setMinimumSize(960, 680)
        self.reference = None
        self.comparison = None
        self.ref_path = None
        self.cmp_path = None
        self.results = []
        self.available_carriers = []
        self.selected_carriers = []
        self.carrier_cache = {}
        self.selected_service = "amount_comparison"
        self.tabs = {}
        self._apply_style()
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.home_page = self._build_home()
        self.work_page = self._build_work_page()
        self.result_page = self._build_result_page()
        for page in (self.home_page, self.work_page, self.result_page):
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(self.home_page)

    def _apply_style(self):
        fusion = QStyleFactory.create("Fusion")
        if fusion:
            QApplication.setStyle(fusion)
        palette = QApplication.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#20312f"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#267b66"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        QApplication.setPalette(palette)
        self.setStyleSheet("""
            QWidget { font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; font-size: 14px; color: #20312f; }
            QMainWindow { background: #f4f7f5; }
            QLabel#heroTitle { color: white; font-size: 38px; font-weight: 800; }
            QLabel#heroSub { color: white; font-size: 17px; }
            QLabel#pageTitle { font-size: 24px; font-weight: 750; color: #173a35; }
            QLabel#muted { color: #71817d; }
            QFrame#serviceCard { background: rgba(255,255,255,238); border: 1px solid rgba(255,255,255,210); border-radius: 18px; }
            QFrame#serviceCard:hover { background: white; border: 2px solid #70b59d; }
            QGroupBox { background: white; border: 1px solid #dce6e1; border-radius: 12px; margin-top: 12px; padding: 12px; font-weight: 650; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #315a50; }
            QPushButton { background: #267b66; color: white; border: 0; border-radius: 9px; padding: 10px 16px; font-weight: 650; }
            QPushButton:hover { background: #1e6857; }
            QPushButton#secondary { background: #e8f0ec; color: #315a50; }
            QPushButton#secondary:hover { background: #dbe9e2; }
            QPushButton#serviceTitle { font-size: 20px; text-align: left; background: transparent; color: #173a35; padding: 0; }
            QComboBox, QLineEdit { background: white; color: #20312f; border: 1px solid #d7e1dc; border-radius: 7px; padding: 7px; }
            QComboBox QAbstractItemView { background: #ffffff; color: #20312f; selection-background-color: #267b66; selection-color: #ffffff; outline: 0; }
            QScrollBar:vertical { background: #edf2ef; width: 15px; margin: 3px 2px 3px 2px; border-radius: 7px; }
            QScrollBar::handle:vertical { background: #93b2a5; min-height: 30px; border-radius: 7px; }
            QScrollBar::handle:vertical:hover { background: #668f7e; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; border: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            QScrollBar:horizontal { background: #edf2ef; height: 15px; margin: 2px 3px; border-radius: 7px; }
            QScrollBar::handle:horizontal { background: #93b2a5; min-width: 30px; border-radius: 7px; }
            QScrollBar::handle:horizontal:hover { background: #668f7e; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; border: none; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
            QPushButton#headerStep { background: #e8f0ec; color: #315a50; border: 1px solid #d7e1dc; border-radius: 7px; padding: 2px; font-size: 11px; }
            QPushButton#headerStep:hover { background: #dbe9e2; }
            QTableWidget { background: white; border: 1px solid #e1e8e4; border-radius: 8px; gridline-color: #edf1ef; alternate-background-color: #f7faf8; }
            QHeaderView::section { background: #eaf2ee; color: #315a50; padding: 8px; border: 0; font-weight: 700; }
        """)

    @staticmethod
    def _combo():
        combo = QComboBox()
        combo.setView(QListView())
        combo.setStyleSheet("QComboBox { background: white; color: #20312f; } QComboBox QAbstractItemView { background: white; color: #20312f; selection-background-color: #267b66; selection-color: white; }")
        return combo

    def _build_home(self):
        page = ImageBackground(BACKGROUND)
        outer = QVBoxLayout(page)
        outer.setContentsMargins(70, 50, 70, 50)
        outer.addStretch(2)
        brand = QLabel("CONTAINER WORKBENCH")
        brand.setStyleSheet("color: #d8efe5; letter-spacing: 3px; font-size: 13px; font-weight: 700;")
        title = QLabel("엑셀 업무를\n더 간단하게")
        title.setObjectName("heroTitle")
        subtitle = QLabel("파일을 비교하고, 필요한 결과를 한눈에 확인하세요.")
        subtitle.setObjectName("heroSub")
        outer.addWidget(brand)
        outer.addSpacing(12)
        outer.addWidget(title)
        outer.addSpacing(10)
        outer.addWidget(subtitle)
        outer.addSpacing(34)
        cards = QHBoxLayout()
        cards.setSpacing(18)
        cards.addWidget(self._service_card("금액 비교", "컨테이너별 기준 금액과 비교 금액의 차이를 확인합니다.", "amount_comparison", "₩"))
        cards.addWidget(self._service_card("번호 대조", "두 파일의 컨테이너 번호 누락과 중복을 찾습니다.", "container_reconciliation", "#"))
        outer.addLayout(cards)
        outer.addStretch(3)
        footer = QLabel("모든 파일은 이 컴퓨터에서 처리됩니다")
        footer.setStyleSheet("color: white; font-size: 12px;")
        outer.addWidget(footer)
        return page

    def _service_card(self, title, description, service, icon):
        card = QFrame()
        card.setObjectName("serviceCard")
        card.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        mark = QLabel(icon)
        mark.setStyleSheet("font-size: 28px; color: #348a70; font-weight: 800;")
        heading = QPushButton(title)
        heading.setObjectName("serviceTitle")
        heading.clicked.connect(lambda: self.open_service(service))
        detail = QLabel(description)
        detail.setWordWrap(True)
        detail.setMinimumHeight(42)
        detail.setStyleSheet("color: #71817d;")
        action = QPushButton("서비스 시작  →")
        action.clicked.connect(lambda: self.open_service(service))
        layout.addWidget(mark)
        layout.addWidget(heading)
        layout.addWidget(detail)
        layout.addStretch()
        layout.addWidget(action)
        card.mousePressEvent = lambda event: self.open_service(service)
        return card

    def go_home(self):
        self.reset_work_state()
        self.stack.setCurrentWidget(self.home_page)

    def reset_work_state(self):
        if hasattr(self, "compare_scope"):
            self.compare_scope.setCurrentIndex(0)
        self.reference = self.comparison = None
        self.ref_path = self.cmp_path = None
        self.results = []
        self.available_carriers = []
        self.selected_carriers = []
        self.carrier_cache.clear()
        self.update_carrier_selection_display()
        for tab in self.tabs.values():
            tab["label"].setText("선택된 파일 없음")
            tab["sheet"].blockSignals(True)
            tab["sheet"].clear()
            tab["sheet"].blockSignals(False)
            tab["header_value"].setText("1행")
            tab["max_header_row"] = 0
            tab["info"].setText("자동 추정 · 파일을 선택하세요")
            tab["table"].clear()
            tab["table"].setRowCount(0)
            tab["table"].setColumnCount(0)
        for combo in (self.ref_key, self.ref_carrier, self.conditional_amount, self.ref_amount,
                      self.cmp_key, self.cmp_amount):
            combo.clear()
        self.result_summary.clear()
        self.result_count.clear()
        self.result_filter.clear()
        self.result_filter.addItem("전체", "전체")
        self.result_table.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)

    def open_service(self, service):
        self.selected_service = service
        self.service_title.setText("컨테이너 금액 비교" if service == "amount_comparison" else "컨테이너 번호 대조")
        self.update_service_fields()
        self.stack.setCurrentWidget(self.work_page)

    def _build_work_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 20, 28, 22)
        top = QHBoxLayout()
        back = QPushButton("← 처음 화면")
        back.setObjectName("secondary")
        back.clicked.connect(self.go_home)
        self.service_title = QLabel("서비스")
        self.service_title.setObjectName("pageTitle")
        top.addWidget(back)
        top.addSpacing(12)
        top.addWidget(self.service_title)
        top.addStretch()
        layout.addLayout(top)

        files = QHBoxLayout()
        files.setSpacing(14)
        self.ref_tab = self._file_card("reference", "기준 파일")
        self.cmp_tab = self._file_card("comparison", "비교 파일")
        files.addWidget(self.ref_tab["box"], 1)
        files.addWidget(self.cmp_tab["box"], 1)
        layout.addLayout(files, 4)

        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("비교 범위"))
        self.compare_scope = self._combo()
        self.compare_scope.addItem("필터와 상관없이 전체 행", "all")
        self.compare_scope.addItem("엑셀에서 필터된 행만", "visible")
        self.compare_scope.setMinimumWidth(260)
        self.compare_scope.currentIndexChanged.connect(lambda _index: self.populate_carrier_options())
        scope_row.addWidget(self.compare_scope)
        scope_row.addWidget(QLabel("※ 저장된 파일에서 숨김 처리된 행을 기준으로 합니다."))
        scope_row.addStretch()
        layout.addLayout(scope_row)

        self.plan_box = QGroupBox("비교할 항목 선택")
        mapping_row = QHBoxLayout(self.plan_box)
        mapping_row.setSpacing(14)
        self.ref_mapping, ref_layout = self._mapping_card("기준 파일")
        self.cmp_mapping, cmp_layout = self._mapping_card("비교 파일")
        mapping_row.addWidget(self.ref_mapping, 1)
        mapping_row.addWidget(self.cmp_mapping, 1)
        layout.addWidget(self.plan_box, 3)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.run_button = QPushButton("설정 확인 후 비교 시작")
        self.run_button.clicked.connect(self.approve_and_run)
        bottom.addWidget(self.run_button)
        layout.addLayout(bottom)
        self.update_service_fields()
        return page

    def _file_card(self, key, title):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        file_row = QHBoxLayout()
        button = QPushButton("파일 선택")
        label = QLabel("선택된 파일 없음")
        label.setObjectName("muted")
        label.setWordWrap(True)
        button.clicked.connect(lambda checked=False, file_key=key: self.pick_file(file_key))
        file_row.addWidget(button)
        file_row.addWidget(label, 1)
        layout.addLayout(file_row)
        sheet_row = QHBoxLayout()
        sheet_row.addWidget(QLabel("시트명"))
        sheet = self._combo()
        sheet_row.addWidget(sheet, 1)
        layout.addLayout(sheet_row)
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("헤더 행"))
        header_value = QLabel("1행")
        header_value.setAlignment(Qt.AlignCenter)
        header_value.setMinimumWidth(58)
        header_value.setStyleSheet("background: #eaf2ee; color: #315a50; border-radius: 7px; padding: 5px 8px; font-weight: 700;")
        up_button = QPushButton("▲")
        down_button = QPushButton("▼")
        for step_button in (up_button, down_button):
            step_button.setObjectName("headerStep")
            step_button.setFixedSize(34, 30)
            step_button.setToolTip("헤더 행을 한 줄씩 조정")
        header_row.addWidget(header_value)
        header_row.addWidget(up_button)
        header_row.addWidget(down_button)
        info = QLabel("자동 추정 · 파일을 선택하세요")
        info.setObjectName("muted")
        header_row.addWidget(info, 1)
        layout.addLayout(header_row)
        hint = QLabel("헤더는 보통 시트 앞쪽에 있어요. 자동 선택을 확인하고 화살표로 조정하세요.")
        hint.setObjectName("muted")
        hint.setStyleSheet("color: #71817d; font-size: 11px;")
        layout.addWidget(hint)
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(160)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, 1)
        tab = {"box": box, "table": table, "label": label, "sheet": sheet,
               "header_value": header_value, "header_up": up_button, "header_down": down_button,
               "max_header_row": 0, "info": info, "key": key}
        self.tabs[key] = tab
        sheet.currentTextChanged.connect(lambda name: self.select_sheet(key, name))
        up_button.clicked.connect(lambda: self.step_header_row(key, -1))
        down_button.clicked.connect(lambda: self.step_header_row(key, 1))
        return tab

    def _mapping_card(self, title):
        group = QGroupBox(title)
        form = QFormLayout(group)
        if title == "기준 파일":
            self.ref_key = self._combo()
            self.ref_carrier = self._combo()
            self.carrier_select_button = QPushButton("운송사 선택")
            self.carrier_select_button.clicked.connect(self.open_carrier_dialog)
            self.carrier_selected_label = QLabel("선택 안 함 · 기본 금액 컬럼 사용")
            self.carrier_selected_label.setWordWrap(True)
            self.carrier_selected_label.setObjectName("muted")
            self.carrier_selection_widget = QWidget()
            carrier_row = QHBoxLayout(self.carrier_selection_widget)
            carrier_row.setContentsMargins(0, 0, 0, 0)
            carrier_row.addWidget(self.carrier_select_button)
            carrier_row.addWidget(self.carrier_selected_label, 1)
            self.conditional_amount = self._combo()
            self.ref_amount = self._combo()
            form.addRow("컨테이너 컬럼명", self.ref_key)
            self.ref_carrier_label = QLabel("운송사 컬럼명")
            self.ref_carrier_label.setBuddy(self.ref_carrier)
            form.addRow(self.ref_carrier_label, self.ref_carrier)
            self.carrier_list_label = QLabel("조건을 적용할 운송사")
            form.addRow(self.carrier_list_label, self.carrier_selection_widget)
            self.ref_carrier.currentTextChanged.connect(self.populate_carrier_options)
            self.conditional_amount_label = QLabel("선택한 운송사의 금액 컬럼")
            form.addRow(self.conditional_amount_label, self.conditional_amount)
            self.ref_amount_label = QLabel("그 외 운송사의 금액 컬럼")
            form.addRow(self.ref_amount_label, self.ref_amount)
        else:
            self.cmp_key = self._combo()
            self.cmp_amount = self._combo()
            form.addRow("컨테이너 컬럼명", self.cmp_key)
            self.cmp_amount_label = QLabel("비교 파일의 금액 컬럼")
            form.addRow(self.cmp_amount_label, self.cmp_amount)
        return group, form

    def pick_file(self, key):
        path, _ = QFileDialog.getOpenFileName(
            self, "엑셀 파일 선택", str(Path.home() / "Desktop"), "Excel files (*.xlsx *.xlsm *.xls)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if not path:
            return
        progress = self._progress_dialog("시트와 미리보기를 불러오는 중...")
        try:
            data = load_workbook(path)
            tab = self.tabs[key]
            if key == "reference":
                self.reference, self.ref_path = data, path
                self.available_carriers = []
                self.selected_carriers = []
                self.carrier_cache.clear()
                self.update_carrier_selection_display()
            else:
                self.comparison, self.cmp_path = data, path
            tab["label"].setText(Path(path).name)
            sheet_combo = tab["sheet"]
            sheet_combo.blockSignals(True)
            sheet_combo.clear()
            sheet_combo.addItems(data.keys())
            sheet_combo.blockSignals(False)
            if data:
                name = sheet_combo.currentText()
                self.select_sheet(key, name)
            self.populate_plan_columns()
        except Exception as exc:
            self.show_message(QMessageBox.Icon.Critical, "파일을 열 수 없어요", str(exc))
        finally:
            progress.close()

    def select_sheet(self, key, name):
        data = self.reference if key == "reference" else self.comparison
        tab = self.tabs[key]
        if not data or name not in data:
            return
        info = data[name]
        if not info.get("hidden_rows_checked"):
            path = self.ref_path if key == "reference" else self.cmp_path
            info = load_sheet(path, name, info["header_row"])
            data[name] = info
        tab["max_header_row"] = info["max_header_row"]
        tab["header_value"].setText(f"{info['header_row'] + 1}행")
        preview_count = len(info["preview"])
        hidden_count = info.get("hidden_data_rows", 0)
        hidden_note = f" · 숨김 {hidden_count:,}행 제외" if hidden_count else ""
        tab["info"].setText(f"자동 추정 · 미리보기 {preview_count}행{hidden_note} · 전체는 실행 시 읽음")
        self.show_frame(tab["table"], info["preview"])
        self.populate_plan_columns()

    def step_header_row(self, key, delta):
        tab = self.tabs[key]
        if not (self.ref_path if key == "reference" else self.cmp_path):
            return
        current = int(tab["header_value"].text().removesuffix("행"))
        next_row = max(1, min(tab["max_header_row"] + 1, current + delta))
        if next_row == current:
            return
        tab["header_value"].setText(f"{next_row}행")
        self.change_header_row(key, next_row)

    def change_header_row(self, key, row_number):
        path = self.ref_path if key == "reference" else self.cmp_path
        data = self.reference if key == "reference" else self.comparison
        sheet_combo = self.tabs[key]["sheet"]
        if not path or not data or not sheet_combo.currentText():
            return
        try:
            name = sheet_combo.currentText()
            info = load_sheet(path, name, row_number - 1)
            data[name] = info
            tab = self.tabs[key]
            tab["header_value"].setText(f"{row_number}행")
            hidden_count = info.get("hidden_data_rows", 0)
            hidden_note = f" · 숨김 {hidden_count:,}행 제외" if hidden_count else ""
            tab["info"].setText(f"직접 선택 · 미리보기 {len(info['preview'])}행{hidden_note} · 전체는 실행 시 읽음")
            self.show_frame(tab["table"], info["preview"])
            self.populate_plan_columns()
        except Exception as exc:
            self.show_message(QMessageBox.Icon.Critical, "헤더 행을 읽을 수 없어요", str(exc))

    def populate_plan_columns(self):
        if self.reference and self.ref_tab["sheet"].currentText():
            columns = self.reference[self.ref_tab["sheet"].currentText()]["columns"]
            for combo in (self.ref_key, self.ref_carrier, self.ref_amount, self.conditional_amount):
                self.set_items(combo, columns)
            self.select_candidate(self.ref_key, ["CON'T NO.", "CONTAINER NO", "컨테이너 번호"])
            self.select_candidate(self.ref_carrier, ["운송사", "선사", "CARRIER"])
            self.select_candidate(self.ref_amount, ["하불액", "청구액"])
            self.select_candidate(self.conditional_amount, ["청구액", "하불액"])
            self.populate_carrier_options()
        if self.comparison and self.cmp_tab["sheet"].currentText():
            columns = self.comparison[self.cmp_tab["sheet"].currentText()]["columns"]
            self.set_items(self.cmp_key, columns)
            self.set_items(self.cmp_amount, columns)
            self.select_candidate(self.cmp_key, ["CONTANER NO.", "CONTAINER NO.", "CONTAINER NO"])
            self.select_candidate(self.cmp_amount, ["TRCV", "AMOUNT", "금액"])

    def _carrier_cache_key(self):
        if (not self.reference or not self.ref_path or not self.ref_tab["sheet"].currentText()
                or self.ref_carrier.currentIndex() <= 0):
            return None
        sheet = self.ref_tab["sheet"].currentText()
        info = self.reference[sheet]
        column = self._selected_column(self.ref_carrier)
        position = info["column_positions"][info["columns"].index(column)]
        visible_only = self.compare_scope.currentData() == "visible"
        return self.ref_path, sheet, info["header_row"], column, position, visible_only

    def populate_carrier_options(self, *signal_args):
        previously_selected = set() if signal_args else set(self.selected_carriers)
        cache_key = self._carrier_cache_key()
        self.available_carriers = self.carrier_cache.get(cache_key, []) if cache_key else []
        self.selected_carriers = [value for value in self.available_carriers if value in previously_selected]
        self.update_carrier_selection_display()

    def update_carrier_selection_display(self):
        if not hasattr(self, "carrier_select_button"):
            return
        self.carrier_select_button.setText(f"운송사 선택 ({len(self.selected_carriers)})")
        can_open = bool(self.ref_path and self.reference and self.ref_tab["sheet"].currentText() and self.ref_carrier.currentIndex() > 0)
        self.carrier_select_button.setEnabled(can_open)
        if self.selected_carriers:
            self.carrier_selected_label.setText("선택됨: " + " · ".join(self.selected_carriers))
            self.carrier_selected_label.setStyleSheet("color: #315a50; background: #eaf2ee; border-radius: 7px; padding: 7px;")
        elif can_open and self.available_carriers:
            self.carrier_selected_label.setText("선택 안 함 · 모든 운송사에 기본 금액 컬럼 사용")
            self.carrier_selected_label.setStyleSheet("color: #71817d;")
        elif can_open:
            self.carrier_selected_label.setText("운송사 선택을 누르면 해당 시트의 목록을 불러옵니다")
            self.carrier_selected_label.setStyleSheet("color: #71817d;")
        else:
            self.carrier_selected_label.setText("운송사 컬럼을 선택하면 목록을 불러올 수 있어요")
            self.carrier_selected_label.setStyleSheet("color: #71817d;")

    def _progress_dialog(self, message):
        progress = QProgressDialog(message, "", 0, 0, self)
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setStyleSheet("QProgressDialog { background: #ffffff; color: #20312f; } QLabel { color: #20312f; }")
        progress.show()
        QApplication.processEvents()
        return progress

    def open_carrier_dialog(self):
        cache_key = self._carrier_cache_key()
        if not cache_key:
            return
        if cache_key not in self.carrier_cache:
            progress = self._progress_dialog("운송사 목록을 불러오는 중...")
            try:
                path, sheet, header, column, position, visible_only = cache_key
                self.carrier_cache[cache_key] = load_column_values(
                    path, sheet, header, position, visible_only=visible_only)
            except Exception as exc:
                self.show_message(QMessageBox.Icon.Critical, "운송사 목록을 읽을 수 없어요", str(exc))
                return
            finally:
                progress.close()
            self.available_carriers = self.carrier_cache[cache_key]
            self.update_carrier_selection_display()
        if not self.available_carriers:
            self.show_message(QMessageBox.Icon.Information, "운송사 없음", "선택한 운송사 컬럼에 값이 없습니다.")
            return
        dialog = QDialog(self)
        current_sheet = self.ref_tab["sheet"].currentText()
        current_column = self._selected_column(self.ref_carrier)
        dialog.setWindowTitle(f"{current_sheet} · {current_column} 운송사 선택")
        dialog.resize(420, 500)
        dialog.setStyleSheet("""
            QDialog { background: #ffffff; color: #20312f; }
            QLabel { color: #20312f; }
            QLineEdit, QListWidget { background: #ffffff; color: #20312f; border: 1px solid #d7e1dc; border-radius: 7px; padding: 6px; }
            QPushButton#carrierCheck { background: #ffffff; color: #ffffff; border: 2px solid #627d71; border-radius: 5px; padding: 0; font-size: 14px; font-weight: 800; }
            QPushButton#carrierCheck:checked { background: #267b66; color: #ffffff; border-color: #267b66; }
            QPushButton { background: #e8f0ec; color: #315a50; border: 1px solid #d7e1dc; border-radius: 7px; padding: 7px 12px; }
            QPushButton:hover { background: #dbe9e2; }
            QDialogButtonBox QPushButton { background: #267b66; color: #ffffff; }
        """)
        layout = QVBoxLayout(dialog)
        description = QLabel(f"'{current_sheet}' 시트의 '{current_column}' 목록입니다. 선택한 운송사에만 조건 금액 컬럼을 적용합니다.")
        description.setWordWrap(True)
        search = QLineEdit()
        search.setPlaceholderText("운송사 이름 검색")
        options = QListWidget()
        options.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        options.setAlternatingRowColors(True)
        for carrier in self.available_carriers:
            item = QListWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, carrier)
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 0, 4, 0)
            check_button = QPushButton("✓")
            check_button.setObjectName("carrierCheck")
            check_button.setCheckable(True)
            check_button.setFixedSize(22, 22)
            check_button.setChecked(carrier in self.selected_carriers)
            carrier_label = QLabel(carrier)
            carrier_label.setStyleSheet("color: #20312f; background: transparent; padding-left: 6px;")
            row_layout.addWidget(check_button)
            row_layout.addWidget(carrier_label)
            row_layout.addStretch()
            item.setSizeHint(row.sizeHint())
            options.addItem(item)
            options.setItemWidget(item, row)
        search.textChanged.connect(lambda text: self.filter_carrier_options(options, text))
        selection_actions = QHBoxLayout()
        select_all = QPushButton("모두 선택")
        clear_all = QPushButton("선택 해제")
        select_all.clicked.connect(lambda: self.set_carrier_checks(options, True))
        clear_all.clicked.connect(lambda: self.set_carrier_checks(options, False))
        selection_actions.addWidget(select_all)
        selection_actions.addWidget(clear_all)
        selection_actions.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("선택 적용")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(description)
        layout.addWidget(search)
        layout.addLayout(selection_actions)
        layout.addWidget(options, 1)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_carriers = [
                options.item(i).data(Qt.ItemDataRole.UserRole) for i in range(options.count())
                if options.itemWidget(options.item(i)).findChild(QPushButton, "carrierCheck").isChecked()
            ]
            self.update_carrier_selection_display()

    @staticmethod
    def filter_carrier_options(options, query):
        query = query.strip().casefold()
        for index in range(options.count()):
            item = options.item(index)
            carrier = str(item.data(Qt.ItemDataRole.UserRole) or "")
            item.setHidden(query not in carrier.casefold())

    @staticmethod
    def set_carrier_checks(options, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for index in range(options.count()):
            if not options.item(index).isHidden():
                check_button = options.itemWidget(options.item(index)).findChild(QPushButton, "carrierCheck")
                check_button.setChecked(checked)

    @staticmethod
    def set_items(combo, values):
        previous = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("— 선택 —")
        combo.addItems([str(value) for value in values])
        index = combo.findText(previous)
        combo.setCurrentIndex(index if index > 0 else 0)
        combo.blockSignals(False)

    @staticmethod
    def _selected_column(combo):
        return combo.currentText() if combo.currentIndex() > 0 else ""

    @staticmethod
    def select_candidate(combo, candidates):
        options = {combo.itemText(i).strip().casefold(): i for i in range(combo.count())}
        for candidate in candidates:
            if candidate.casefold() in options:
                combo.setCurrentIndex(options[candidate.casefold()])
                return

    def update_service_fields(self):
        is_amount = self.selected_service == "amount_comparison"
        widgets = (self.ref_carrier_label, self.ref_carrier, self.carrier_list_label, self.carrier_selection_widget,
                   self.conditional_amount_label, self.conditional_amount, self.ref_amount_label,
                   self.ref_amount, self.cmp_amount_label, self.cmp_amount)
        for widget in widgets:
            widget.setVisible(is_amount)

    def approve_and_run(self):
        if not self.reference or not self.comparison:
            self.show_message(QMessageBox.Icon.Warning, "선택이 필요해요", "파일과 항목을 선택해주세요")
            return
        ref_name, cmp_name = self.ref_tab["sheet"].currentText(), self.cmp_tab["sheet"].currentText()
        ref_key, cmp_key = self._selected_column(self.ref_key), self._selected_column(self.cmp_key)
        if not ref_name or not cmp_name or not ref_key or not cmp_key:
            self.show_message(QMessageBox.Icon.Warning, "선택이 필요해요", "파일과 항목을 선택해주세요")
            return
        ref_info, cmp_info = self.reference[ref_name], self.comparison[cmp_name]
        visible_only = self.compare_scope.currentData() == "visible"
        scope_key = "visible" if visible_only else "all"
        if self.selected_service == "amount_comparison":
            if not self._selected_column(self.ref_amount) or not self._selected_column(self.cmp_amount):
                self.show_message(QMessageBox.Icon.Warning, "선택이 필요해요", "파일과 항목을 선택해주세요")
                return
            selected_carriers = list(self.selected_carriers)
            if selected_carriers and not self._selected_column(self.ref_carrier):
                self.show_message(QMessageBox.Icon.Warning, "선택이 필요해요", "파일과 항목을 선택해주세요")
                return
            if selected_carriers and not self._selected_column(self.conditional_amount):
                self.show_message(QMessageBox.Icon.Warning, "선택이 필요해요", "파일과 항목을 선택해주세요")
                return
        try:
            plan = {
                "service": self.selected_service,
                "reference": {"sheet": ref_name, "container_column": ref_key},
                "comparison": {"sheet": cmp_name, "container_column": cmp_key},
            }
            if self.selected_service == "amount_comparison":
                carrier_column = self._selected_column(self.ref_carrier)
                default_amount_column = self._selected_column(self.ref_amount)
                conditional_amount_column = self._selected_column(self.conditional_amount)
                plan["reference"].update({"carrier_column": carrier_column or None,
                                          "default_amount_column": default_amount_column})
                if selected_carriers:
                    plan["reference"]["amount_rules"] = [
                        {"value": carrier, "amount_column": conditional_amount_column}
                        for carrier in selected_carriers
                    ]
                plan["comparison"]["amount_column"] = self._selected_column(self.cmp_amount)
            config = validate_plan(plan, self.reference, self.comparison)
            config.approved = True
            progress = None
            if (not ref_info.get("loaded") or ref_info.get("loaded_scope") != scope_key
                    or not cmp_info.get("loaded") or cmp_info.get("loaded_scope") != scope_key):
                progress = self._progress_dialog("선택한 시트의 데이터를 불러오는 중...")
            try:
                if not ref_info.get("loaded") or ref_info.get("loaded_scope") != scope_key:
                    previous = ref_info
                    ref_info = load_sheet_data(self.ref_path, ref_name, previous["header_row"], visible_only)
                    ref_info["max_header_row"] = previous["max_header_row"]
                    ref_info["column_positions"] = previous["column_positions"]
                    ref_info["loaded_scope"] = scope_key
                    self.reference[ref_name] = ref_info
                if not cmp_info.get("loaded") or cmp_info.get("loaded_scope") != scope_key:
                    previous = cmp_info
                    cmp_info = load_sheet_data(self.cmp_path, cmp_name, previous["header_row"], visible_only)
                    cmp_info["max_header_row"] = previous["max_header_row"]
                    cmp_info["column_positions"] = previous["column_positions"]
                    cmp_info["loaded_scope"] = scope_key
                    self.comparison[cmp_name] = cmp_info
            finally:
                if progress:
                    progress.close()
            if ref_info["data"].empty or cmp_info["data"].empty:
                self.show_message(QMessageBox.Icon.Warning, "선택이 필요해요", "파일과 항목을 선택해주세요")
                return
            ref_has_container = any(is_valid_container_number(value) for value in ref_info["data"][ref_key])
            cmp_has_container = any(is_valid_container_number(value) for value in cmp_info["data"][cmp_key])
            if not ref_has_container and not cmp_has_container:
                self.show_message(QMessageBox.Icon.Warning, "선택이 필요해요", "파일과 항목을 선택해주세요")
                return
            if self.selected_service == "amount_comparison":
                self.results = compare_amounts(ref_info["data"], cmp_info["data"], config,
                                               ref_info["header_row"], cmp_info["header_row"])
            else:
                self.results = reconcile_containers(ref_info["data"], cmp_info["data"],
                    config.reference.container_column, config.comparison.container_column,
                    ref_info["header_row"], cmp_info["header_row"])
            self.populate_results()
            self.stack.setCurrentWidget(self.result_page)
        except Exception as exc:
            self.show_message(QMessageBox.Icon.Critical, "설정을 확인해 주세요", str(exc))

    def show_message(self, icon, title, text):
        message = QMessageBox(self)
        message.setIcon(icon)
        message.setWindowTitle(title)
        message.setText(text)
        message.setStandardButtons(QMessageBox.StandardButton.Ok)
        message.setStyleSheet("""
            QMessageBox { background: #ffffff; color: #20312f; }
            QMessageBox QLabel { background: transparent; color: #20312f; min-width: 260px; }
            QMessageBox QPushButton { background: #267b66; color: #ffffff; min-width: 76px; padding: 7px 14px; border-radius: 7px; }
        """)
        message.exec()

    def _build_result_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 28)
        top = QHBoxLayout()
        back = QPushButton("← 작업 화면으로")
        back.setObjectName("secondary")
        back.clicked.connect(lambda: self.stack.setCurrentWidget(self.work_page))
        title = QLabel("비교 결과")
        title.setObjectName("pageTitle")
        top.addWidget(back)
        top.addSpacing(14)
        top.addWidget(title)
        top.addStretch()
        self.result_count = QLabel("")
        self.result_count.setStyleSheet("color: #527166; font-weight: 700;")
        top.addWidget(self.result_count)
        layout.addLayout(top)
        self.result_summary = QLabel("")
        self.result_summary.setStyleSheet("background: #eaf2ee; border-radius: 9px; padding: 12px; font-size: 15px; font-weight: 650;")
        layout.addWidget(self.result_summary)
        self.result_help = QLabel("")
        self.result_help.setObjectName("muted")
        self.result_help.setWordWrap(True)
        layout.addWidget(self.result_help)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("결과 보기"))
        self.result_filter = self._combo()
        self.result_filter.addItem("전체", "전체")
        self.result_filter.setMaximumWidth(280)
        self.result_filter.currentIndexChanged.connect(self.update_result_filter)
        filter_row.addWidget(self.result_filter)
        filter_row.addStretch()
        layout.addLayout(filter_row)
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setWordWrap(True)
        self.result_table.setSortingEnabled(True)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.result_table, 1)
        return page

    def populate_results(self):
        counts = Counter(result.status for result in self.results)
        summary = [f"전체 {len(self.results):,}건"] + [f"{status} {count:,}건" for status, count in counts.items()]
        self.result_summary.setText("   ·   ".join(summary))
        scope_label = "엑셀에서 필터된 행만 비교" if self.compare_scope.currentData() == "visible" else "필터와 상관없이 전체 행 비교"
        self.result_help.setText(f"비교 범위: {scope_label} (저장된 파일 기준)\n중복: 같은 컨테이너 번호가 한 파일에 여러 번 있음 · 데이터 오류: 금액이 비었거나 숫자로 바꿀 수 없음")
        self.result_filter.blockSignals(True)
        self.result_filter.clear()
        self.result_filter.addItem(f"전체 ({len(self.results):,}건)", "전체")
        if self.selected_service == "amount_comparison":
            statuses = ["비교 파일 누락", "기준 파일 누락", "금액 불일치", "금액 일치", "중복", "데이터 오류"]
        else:
            statuses = ["양쪽 파일에 존재", "기준 파일에만 존재", "비교 파일에만 존재", "중복"]
        for status in statuses:
            self.result_filter.addItem(f"{status} ({counts.get(status, 0):,}건)", status)
        self.result_filter.blockSignals(False)
        self.result_filter.setCurrentIndex(0)
        self.update_result_filter()

    def update_result_filter(self):
        selected = self.result_filter.currentData()
        records = [result.as_dict() for result in self.results]
        if selected and selected != "전체":
            records = [record for record in records if record["결과"] == selected]
        self.show_dicts(self.result_table, records)
        self.result_count.setText(f"표시 {len(records):,}건 / 전체 {len(self.results):,}건")

    @staticmethod
    def show_frame(table, frame):
        records = frame.fillna("").astype(str).values.tolist()
        table.setRowCount(len(records))
        table.setColumnCount(len(frame.columns))
        table.setHorizontalHeaderLabels([str(column) for column in frame.columns])
        for row, values in enumerate(records):
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()

    @staticmethod
    def show_dicts(table, records):
        table.setSortingEnabled(False)
        headers = [key for key in records[0] if key != "차액"] if records else []
        table.setColumnCount(len(headers))
        table.setRowCount(len(records))
        table.setHorizontalHeaderLabels(headers)
        for row, record in enumerate(records):
            for column, key in enumerate(headers):
                value = record.get(key)
                item = QTableWidgetItem("" if value is None else str(value))
                if key == "결과":
                    matching = "일치" in str(value) and "불일치" not in str(value)
                    item.setForeground(QColor("#267b66" if matching else "#a3523c"))
                table.setItem(row, column, item)
        table.resizeColumnsToContents()
        preferred_widths = {
            "컨테이너 번호": 135, "기준 행 번호": 175, "비교 행 번호": 175,
            "기준 금액": 110, "비교 금액": 110, "차액": 90,
            "운송사": 90, "적용 금액 컬럼": 135, "결과": 120, "상세": 220,
        }
        for column, key in enumerate(headers):
            if key in preferred_widths:
                table.setColumnWidth(column, preferred_widths[key])
        table.resizeRowsToContents()
        table.setSortingEnabled(True)


def run():
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
