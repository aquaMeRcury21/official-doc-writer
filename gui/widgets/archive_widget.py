import json
import os
import shutil
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.knowledge_base_updater import process_all as scan_and_update
from utils.settings import ARCHIVE_DIR


class ArchiveWidget(QWidget):
    scan_finished = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._setup_ui()
        self.scan_finished.connect(self._on_scan_finished)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel('归档管理')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        layout.addSpacing(8)

        status_row = QHBoxLayout()
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #7f8c8d;')
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        self.btn_scan = QPushButton('扫描 kb-inbox 入库')
        self.btn_scan.setObjectName('primaryBtn')
        self.btn_scan.clicked.connect(self._scan_inbox)
        btn_row.addWidget(self.btn_scan)

        self.btn_import = QPushButton('导入文件到归档')
        self.btn_import.setObjectName('secondaryBtn')
        self.btn_import.clicked.connect(self._import_file)
        btn_row.addWidget(self.btn_import)

        self.btn_refresh = QPushButton('刷新列表')
        self.btn_refresh.setObjectName('secondaryBtn')
        self.btn_refresh.clicked.connect(self._refresh)
        btn_row.addWidget(self.btn_refresh)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addSpacing(8)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['文件', '大小', '修改时间', '路径'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        bottom_row = QHBoxLayout()
        self.btn_delete = QPushButton('删除选中')
        self.btn_delete.setObjectName('dangerBtn')
        self.btn_delete.clicked.connect(self._delete_selected)
        bottom_row.addWidget(self.btn_delete)

        self.btn_open_folder = QPushButton('打开所在文件夹')
        self.btn_open_folder.setObjectName('secondaryBtn')
        self.btn_open_folder.clicked.connect(self._open_folder)
        bottom_row.addWidget(self.btn_open_folder)
        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        self._refresh()

    def _scan_inbox(self):
        self.btn_scan.setEnabled(False)
        self.status_label.setText('正在扫描 kb-inbox...')

        def task():
            try:
                result = scan_and_update()
                msg = f'入库完成: {json.dumps(result, ensure_ascii=False)}'
            except Exception as e:
                msg = f'入库失败: {str(e)}'
            self.scan_finished.emit(msg)

        threading.Thread(target=task, daemon=True).start()

    def _on_scan_finished(self, msg):
        self.status_label.setText(msg)
        self.btn_scan.setEnabled(True)
        self._refresh()

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '选择要归档的文件', '', '公文文件 (*.docx *.txt *.md);;所有文件 (*.*)'
        )
        if not path:
            return
        src = Path(path)
        try:
            date_str = datetime.now().strftime('%Y%m%d')
            dst_dir = ARCHIVE_DIR / date_str
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / src.name
            shutil.copy2(str(src), str(dst))
            QMessageBox.information(self, '导入成功', f'已复制到:\n{dst}')
            self.status_label.setText(f'已导入: {src.name}')
            self._refresh()
        except Exception as e:
            QMessageBox.critical(self, '导入失败', str(e))

    def _refresh(self):
        self.table.setRowCount(0)
        archive_path = ARCHIVE_DIR
        if not archive_path.exists():
            return
        files = []
        for root, _, filenames in os.walk(str(archive_path)):
            for fn in filenames:
                if fn.endswith('.txt') or fn.endswith('.docx'):
                    fpath = Path(root) / fn
                    files.append(fpath)
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        self.table.setRowCount(len(files))
        for i, fpath in enumerate(files):
            st = fpath.stat()
            self.table.setItem(i, 0, QTableWidgetItem(fpath.name))
            self.table.setItem(i, 1, QTableWidgetItem(f'{st.st_size / 1024:.1f} KB'))
            mtime = datetime.fromtimestamp(st.st_mtime)
            self.table.setItem(i, 2, QTableWidgetItem(mtime.strftime('%Y-%m-%d %H:%M')))
            rel = fpath.relative_to(archive_path)
            self.table.setItem(i, 3, QTableWidgetItem(str(rel)))
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, str(fpath))

        self.status_label.setText(f'共 {len(files)} 个归档文件')

    def _delete_selected(self):
        rows = set()
        for idx in self.table.selectedIndexes():
            rows.add(idx.row())
        if not rows:
            QMessageBox.warning(self, '提示', '请先选择要删除的文件')
            return
        confirm = QMessageBox.question(
            self,
            '确认删除',
            f'确定要从知识库删除选中的 {len(rows)} 个文件吗？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        for row in sorted(rows, reverse=True):
            item = self.table.item(row, 0)
            fpath = item.data(Qt.ItemDataRole.UserRole)
            if fpath and Path(fpath).exists():
                Path(fpath).unlink()
        self.status_label.setText(f'已删除 {len(rows)} 个文件')
        self._refresh()

    def _open_folder(self):
        path = str(ARCHIVE_DIR)
        if Path(path).exists():
            os.startfile(path)
