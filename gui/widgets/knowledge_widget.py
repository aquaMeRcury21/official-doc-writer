import threading

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from utils.rag_engine import RAGEngine

LAYER_NAMES = {
    'all': '全部知识库',
    'global': '全局知识（政策/讲话）',
    'category': '分类知识（范文）',
    'archive': '归档文稿（查重）',
}


class KnowledgeWidget(QWidget):
    index_loaded = pyqtSignal(str)
    reindex_finished = pyqtSignal(str, bool)
    search_finished = pyqtSignal(list)

    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self.rag = RAGEngine()
        self._setup_ui()
        self.index_loaded.connect(self._on_index_loaded)
        self.reindex_finished.connect(self._on_reindex_finished)
        self.search_finished.connect(self._on_search_finished)
        self._load_index()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel('知识库检索')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        layout.addSpacing(8)

        status_row = QHBoxLayout()
        self.index_status = QLabel('索引状态: 待加载')
        self.index_status.setStyleSheet('color: #7f8c8d;')
        status_row.addWidget(self.index_status)
        status_row.addStretch()
        self.btn_reindex = QPushButton('重建索引')
        self.btn_reindex.setObjectName('secondaryBtn')
        self.btn_reindex.clicked.connect(self._reindex)
        status_row.addWidget(self.btn_reindex)
        layout.addLayout(status_row)

        layout.addSpacing(8)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel('搜索层:'))
        self.layer_combo = QComboBox()
        for key, name in LAYER_NAMES.items():
            self.layer_combo.addItem(name, key)
        self.layer_combo.setMinimumWidth(180)
        search_row.addWidget(self.layer_combo)

        search_row.addWidget(QLabel('关键词:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入搜索关键词...')
        self.search_input.returnPressed.connect(self._search)
        search_row.addWidget(self.search_input, 1)

        self.btn_search = QPushButton('搜索')
        self.btn_search.setObjectName('primaryBtn')
        self.btn_search.clicked.connect(self._search)
        search_row.addWidget(self.btn_search)
        layout.addLayout(search_row)

        layout.addSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.result_list = QListWidget()
        self.result_list.currentItemChanged.connect(self._show_detail)
        splitter.addWidget(self.result_list)

        self.detail_view = QTextBrowser()
        self.detail_view.setOpenExternalLinks(False)
        splitter.addWidget(self.detail_view)

        splitter.setSizes([300, 600])
        layout.addWidget(splitter, 1)

        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #7f8c8d;')
        layout.addWidget(self.status_label)

    def _load_index(self):
        def task():
            try:
                stats = self.rag.stats()
                total = sum(v['chunks'] for v in stats.values())
                parts = []
                for layer, s in stats.items():
                    name = LAYER_NAMES.get(layer, layer)
                    parts.append(f'{name}: {s["chunks"]}片段')
                msg = f'索引已加载，共 {total} 片段 | ' + ' | '.join(parts)
            except Exception:
                msg = '索引未构建，请点击"重建索引"'
            self.index_loaded.emit(msg)

        threading.Thread(target=task, daemon=True).start()

    def _on_index_loaded(self, msg):
        self.index_status.setText(msg)

    def _reindex(self):
        self.btn_reindex.setEnabled(False)
        self.index_status.setText('正在重建索引...')

        def task():
            try:
                results = self.rag.index_all(force=True)
                parts = []
                for layer, r in results.items():
                    name = LAYER_NAMES.get(layer, layer)
                    parts.append(f'{name}: {r["chunks"]}片段')
                msg = '索引重建完成 | ' + ' | '.join(parts)
                ok = True
            except Exception as e:
                msg = f'索引重建失败: {str(e)}'
                ok = False
            self.reindex_finished.emit(msg, ok)

        threading.Thread(target=task, daemon=True).start()

    def _on_reindex_finished(self, msg, ok):
        self.index_status.setText(msg)
        self.btn_reindex.setEnabled(True)

    def _search(self):
        query = self.search_input.text().strip()
        if not query:
            self.status_label.setText('请输入搜索关键词')
            return

        layer = self.layer_combo.currentData()
        if layer == 'all':
            layer = None
        self.btn_search.setEnabled(False)
        self.result_list.clear()
        self.detail_view.setHtml('<p style="color: #7f8c8d;">搜索中...</p>')
        self.status_label.setText(f'正在搜索: {query}')

        def task():
            try:
                results = self.rag.search(query, layer=layer, top_k=10)
            except Exception as e:
                results = [{'text': f'搜索失败: {str(e)}', 'source': '', 'layer': '', 'score': 0}]
            self.search_finished.emit(results)

        threading.Thread(target=task, daemon=True).start()

    def _on_search_finished(self, results):
        self.result_list.clear()
        for r in results:
            text = r.get('text', '')
            source = r.get('source', '')
            score = r.get('score', 0)
            layer_name = LAYER_NAMES.get(r.get('layer', ''), r.get('layer', ''))
            display = f'[score={score:.3f}] {text[:60]}...'
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, r)
            item.setToolTip(f'来源: {source}\n层: {layer_name}\n相关度: {score}')
            self.result_list.addItem(item)

        self.btn_search.setEnabled(True)
        self.status_label.setText(f'搜索完成，找到 {len(results)} 条结果')

    def _show_detail(self, current, previous):
        if not current:
            return
        data = current.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        text = data.get('text', '')
        source = data.get('source', '')
        score = data.get('score', 0)
        layer = data.get('layer', '')
        layer_name = LAYER_NAMES.get(layer, layer)

        html = f"""
        <div style="font-family: SimSun; font-size: 14px;">
            <h3 style="color: #2c3e50;">检索结果详情</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
                <tr>
                    <td style="padding: 4px 8px; color: #7f8c8d; width: 80px;">来源层</td>
                    <td style="padding: 4px 8px;">{layer_name}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; color: #7f8c8d;">相关度</td>
                    <td style="padding: 4px 8px;">{score:.4f}</td>
                </tr>
                <tr>
                    <td style="padding: 4px 8px; color: #7f8c8d;">文件</td>
                    <td style="padding: 4px 8px; word-break: break-all;">{source}</td>
                </tr>
            </table>
            <div style="background: #f8f9fa; border-left: 3px solid #3498db;
                        padding: 12px; line-height: 1.8;">
                {text}
            </div>
        </div>
        """
        self.detail_view.setHtml(html)
