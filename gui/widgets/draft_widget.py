import threading

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.backend import deepseek_client
from utils.file_utils import archive_working_files
from utils.rag_engine import RAGEngine
from utils.settings import ORG_NAME, ORG_SHORT

DOC_TYPES = [
    '通知',
    '请示',
    '报告',
    '函',
    '纪要',
    '工作总结',
    '讲话稿',
    '简报',
    '工作方案',
]


class DraftWidget(QWidget):
    generate_finished = pyqtSignal(str, bool)

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._setup_ui()
        self.generate_finished.connect(self._on_generate_finished)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel('起草公文')
        title.setObjectName('appTitle')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)

        layout.addSpacing(12)

        form = QWidget()
        form.setObjectName('card')
        form.setStyleSheet("""
            #card { background: #fff; border: 1px solid #e0e0e0;
                    border-radius: 6px; padding: 20px; }
        """)
        form_layout = QVBoxLayout(form)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('文种类型:'))
        self.doc_type = QComboBox()
        self.doc_type.addItems(DOC_TYPES)
        self.doc_type.setMinimumWidth(150)
        row1.addWidget(self.doc_type)
        row1.addStretch()
        form_layout.addLayout(row1)

        form_layout.addSpacing(8)
        form_layout.addWidget(QLabel('写作需求:'))
        self.requirement = QPlainTextEdit()
        self.requirement.setPlaceholderText(
            f'请描述需要起草的公文内容要点，例如：\n'
            f'拟于7月中旬召开{ORG_NAME}上半年工作总结会议，'
            f'请各科室负责人参加，总结上半年工作成效，部署下半年任务...'
        )
        self.requirement.setMinimumHeight(120)
        form_layout.addWidget(self.requirement)

        form_layout.addSpacing(8)
        form_layout.addWidget(QLabel('补充信息（可选，供生成参考）:'))
        self.context = QPlainTextEdit()
        self.context.setPlaceholderText(
            '如涉及的具体数据、时间地点、参会人员、需引用上级文件等可在此补充...'
        )
        self.context.setMinimumHeight(80)
        form_layout.addWidget(self.context)

        form_layout.addSpacing(12)
        btn_row = QHBoxLayout()
        self.btn_generate = QPushButton('起草全文')
        self.btn_generate.setObjectName('primaryBtn')
        self.btn_generate.clicked.connect(self._generate)
        self.btn_generate.setMinimumWidth(120)
        btn_row.addWidget(self.btn_generate)

        self.btn_outline = QPushButton('先生成大纲')
        self.btn_outline.setObjectName('secondaryBtn')
        self.btn_outline.clicked.connect(self._generate_outline)
        btn_row.addWidget(self.btn_outline)

        self.btn_clear = QPushButton('清空')
        self.btn_clear.setObjectName('secondaryBtn')
        self.btn_clear.clicked.connect(self._clear)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()
        form_layout.addLayout(btn_row)

        layout.addWidget(form)

        layout.addSpacing(12)

        editor_label = QLabel('编辑区（可手动修改结果）:')
        editor_label.setStyleSheet('font-weight: bold; color: #2c3e50;')
        layout.addWidget(editor_label)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText('生成的公文内容将显示在这里，可手动编辑...')
        self.editor.setMinimumHeight(250)
        layout.addWidget(self.editor, 1)

        btn_row2 = QHBoxLayout()
        self.btn_export = QPushButton('导出为 .docx')
        self.btn_export.setObjectName('successBtn')
        self.btn_export.clicked.connect(self._export)
        btn_row2.addWidget(self.btn_export)

        self.btn_export_txt = QPushButton('仅导出 .txt')
        self.btn_export_txt.setObjectName('secondaryBtn')
        self.btn_export_txt.clicked.connect(self._export_txt)
        btn_row2.addWidget(self.btn_export_txt)

        btn_row2.addStretch()
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #7f8c8d;')
        btn_row2.addWidget(self.status_label)
        layout.addLayout(btn_row2)

    def _set_buttons_enabled(self, enabled):
        self.btn_generate.setEnabled(enabled)
        self.btn_outline.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.btn_export_txt.setEnabled(enabled)

    def _generate(self):
        doc_type = self.doc_type.currentText()
        req = self.requirement.toPlainText().strip()
        if not req:
            QMessageBox.warning(self, '提示', '请先输入写作需求')
            return
        ctx = self.context.toPlainText().strip()
        full_req = f'起草一份{doc_type}。\n需求：{req}'
        if ctx:
            full_req += f'\n补充信息：{ctx}'
        self._do_generate(full_req)

    def _generate_outline(self):
        doc_type = self.doc_type.currentText()
        req = self.requirement.toPlainText().strip()
        if not req:
            QMessageBox.warning(self, '提示', '请先输入写作需求')
            return
        ctx = self.context.toPlainText().strip()
        full_req = f'请为以下{doc_type}生成大纲（仅列标题结构）。\n需求：{req}'
        if ctx:
            full_req += f'\n补充信息：{ctx}'
        self._do_generate(full_req, outline=True)

    def _do_generate(self, prompt, outline=False):
        self._set_buttons_enabled(False)
        self.status_label.setText('正在生成，请稍候...')
        self.editor.clear()

        def task():
            try:
                client = deepseek_client()
                task_type = 'outline' if outline else 'draft'
                result = client.chat(prompt, task_type=task_type)
                content = result.content or '生成失败'
            except Exception as e:
                content = f'错误: {str(e)}'
            self.generate_finished.emit(content, outline)

        threading.Thread(target=task, daemon=True).start()

    def _on_generate_finished(self, content, outline):
        self.editor.setPlainText(content)
        self._set_buttons_enabled(True)
        self.status_label.setText(
            '大纲已生成，可继续完善' if outline else '起草完成，可手动编辑后导出'
        )
        self.main.status_message('公文生成完成')

    def _export(self):
        content = self.editor.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, '提示', '编辑区内容为空，无法导出')
            return
        try:
            from utils.document_generator import write_docx

            dt = self.doc_type.currentText()
            path = write_docx(
                title=self._guess_title(content) or f'{ORG_SHORT}关于[事项]的{dt}',
                body=content.split('\n'),
                category='0001——业务工作',
                filename_stem=f'{ORG_SHORT}关于[事项]的{dt}',
            )
            archive_working_files(str(path.parent))
            try:
                RAGEngine()._build_layer_index('archive', force=True)
            except Exception:
                pass
            QMessageBox.information(self, '导出成功', f'文件已保存至:\n{path}')
            self.status_label.setText(f'已导出: {path}')
            self.main.status_message('公文导出成功')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', str(e))

    def _export_txt(self):
        content = self.editor.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, '提示', '编辑区内容为空')
            return
        from datetime import datetime

        from utils.settings import ROOT

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = ROOT / 'output' / f'draft_{ts}.txt'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        QMessageBox.information(self, '导出成功', f'文本已保存至:\n{path}')
        self.status_label.setText(f'已导出: {path}')

    def _clear(self):
        self.requirement.clear()
        self.context.clear()
        self.editor.clear()
        self.status_label.setText('')

    @staticmethod
    def _guess_title(content):
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        for line in lines[:5]:
            if '关于' in line and (
                '通知' in line
                or '请示' in line
                or '报告' in line
                or '函' in line
                or '纪要' in line
                or '总结' in line
            ):
                return line
        return None
