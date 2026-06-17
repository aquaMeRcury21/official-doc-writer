import threading

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.backend import deepseek_client


class ProofreadWidget(QWidget):
    proofread_finished = pyqtSignal(str)

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._setup_ui()
        self.proofread_finished.connect(self._on_proofread_finished)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel('公文校对')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        layout.addSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel('待校对文稿:'))
        self.input_area = QPlainTextEdit()
        self.input_area.setPlaceholderText('粘贴需要校对的公文全文...')
        left_layout.addWidget(self.input_area, 1)

        btn_row = QHBoxLayout()
        self.btn_proofread = QPushButton('开始校对')
        self.btn_proofread.setObjectName('primaryBtn')
        self.btn_proofread.clicked.connect(self._proofread)
        btn_row.addWidget(self.btn_proofread)

        self.btn_clear = QPushButton('清空')
        self.btn_clear.setObjectName('secondaryBtn')
        self.btn_clear.clicked.connect(self._clear)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel('校对报告将显示在此处')
        self.status_label.setStyleSheet('color: #7f8c8d;')
        right_layout.addWidget(self.status_label)

        self.result_area = QTextBrowser()
        self.result_area.setOpenExternalLinks(False)
        right_layout.addWidget(self.result_area, 1)

        splitter.addWidget(right)
        splitter.setSizes([500, 500])

        layout.addWidget(splitter, 1)

    def _proofread(self):
        text = self.input_area.toPlainText().strip()
        if not text:
            self.result_area.setHtml('<p style="color: #e74c3c;">请先粘贴待校对的文稿</p>')
            return

        self.btn_proofread.setEnabled(False)
        self.status_label.setText('正在校对，请稍候...')
        self.result_area.setHtml(
            '<p style="color: #7f8c8d;">调用 AI 深度校对中，预计需要 10-30 秒...</p>'
        )

        def task():
            try:
                client = deepseek_client()
                result = client.proofread(text)
                content = result.content or '校对无返回结果'
                html = self._format_report(content)
            except Exception as e:
                html = f'<p style="color: #e74c3c;">校对失败: {str(e)}</p>'
            self.proofread_finished.emit(html)

        threading.Thread(target=task, daemon=True).start()

    def _on_proofread_finished(self, html):
        self.result_area.setHtml(html)
        self.btn_proofread.setEnabled(True)
        self.status_label.setText('校对完成')

    def _clear(self):
        self.input_area.clear()
        self.result_area.clear()
        self.status_label.setText('')

    @staticmethod
    def _format_report(text):
        lines = text.split('\n')
        html_parts = ['<div style="font-family: SimSun; font-size: 14px;">']
        for line in lines:
            stripped = line.strip()
            if not stripped:
                html_parts.append('<br>')
            elif stripped.startswith('#') or stripped.startswith('---'):
                html_parts.append(
                    f'<h3 style="color: #2c3e50; border-bottom: 2px solid '
                    f'#3498db; padding-bottom: 4px;">'
                    f'{stripped.lstrip("#").lstrip("-")}</h3>'
                )
            elif any(kw in stripped for kw in ('错误', '问题', '⚠', '✗', '×')):
                html_parts.append(f'<p style="color: #e74c3c; margin: 4px 0;">{stripped}</p>')
            elif any(kw in stripped for kw in ('建议', '修正', '→', '➜')):
                html_parts.append(f'<p style="color: #27ae60; margin: 4px 0;">{stripped}</p>')
            elif any(kw in stripped for kw in ('原文', '原句')):
                html_parts.append(f'<p style="color: #8e44ad; margin: 4px 0;">{stripped}</p>')
            else:
                html_parts.append(f'<p style="margin: 2px 0;">{stripped}</p>')
        html_parts.append('</div>')
        return ''.join(html_parts)
