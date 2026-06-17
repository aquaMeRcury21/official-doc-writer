from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.widgets.archive_widget import ArchiveWidget
from gui.widgets.draft_widget import DraftWidget
from gui.widgets.knowledge_widget import KnowledgeWidget
from gui.widgets.proofread_widget import ProofreadWidget
from gui.widgets.settings_widget import SettingsWidget

ROOT = Path(__file__).resolve().parent.parent


class MainWindow(QMainWindow):
    NAV_ITEMS = [
        ('draft', '起草', '📝'),
        ('knowledge', '知识库', '🔍'),
        ('proofread', '校对', '✅'),
        ('archive', '归档', '📁'),
        ('settings', '设置', '⚙'),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle('公文撰写工作站')
        self.resize(1280, 800)
        self._setup_ui()
        self._load_styles()
        self._nav_buttons = {}
        self._setup_nav()
        self._setup_content()
        self._setup_cost_timer()
        self._switch_page('draft')

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setObjectName('sidebar')
        self.sidebar.setFixedWidth(200)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_layout.setSpacing(0)

        title = QLabel('公文撰写工作站')
        title.setObjectName('appTitle')
        self.sidebar_layout.addWidget(title)

        self.cost_label = QLabel('调用统计加载中...')
        self.cost_label.setObjectName('costLabel')
        self.sidebar_layout.addWidget(self.cost_label)
        self.sidebar_layout.addSpacing(10)

        self.sidebar_layout.addStretch()

        version = QLabel('v0.1.0')
        version.setObjectName('costLabel')
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_layout.addWidget(version)

        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName('contentArea')
        layout.addWidget(self.stack, 1)

    def _load_styles(self):
        qss_path = Path(__file__).parent / 'resources' / 'styles.qss'
        if qss_path.exists():
            with open(qss_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

    def _setup_nav(self):
        for key, label, icon in self.NAV_ITEMS:
            btn = QPushButton(f'{icon}  {label}')
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._switch_page(k))
            self._nav_buttons[key] = btn
            pos = self.sidebar_layout.count() - 2
            self.sidebar_layout.insertWidget(pos, btn)

    def _setup_content(self):
        self.pages = {}
        for key, _, _ in self.NAV_ITEMS:
            widget = self._create_page(key)
            self.pages[key] = widget
            self.stack.addWidget(widget)

    def _create_page(self, key):
        if key == 'draft':
            return DraftWidget(self)
        elif key == 'knowledge':
            return KnowledgeWidget(self)
        elif key == 'proofread':
            return ProofreadWidget(self)
        elif key == 'archive':
            return ArchiveWidget(self)
        elif key == 'settings':
            return SettingsWidget(self)
        return QWidget()

    def _switch_page(self, key):
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)
        self.stack.setCurrentWidget(self.pages[key])

    def _setup_cost_timer(self):
        self._cost_timer = QTimer(self)
        self._cost_timer.timeout.connect(self._update_cost)
        self._cost_timer.start(30000)
        QTimer.singleShot(1000, self._update_cost)

    def _update_cost(self):
        try:
            from utils.cost_tracker import get_tracker

            tracker = get_tracker()
            today = tracker.today_cost()
            budget = tracker.daily_budget
            pct = (today / budget * 100) if budget > 0 else 0
            status = '超预算' if pct >= 100 else ('紧张' if pct > 80 else '正常')
            self.cost_label.setText(
                f'今日调用: ¥{today:.4f} / ¥{budget:.2f} ({pct:.1f}%) [{status}]'
            )
        except Exception:
            self.cost_label.setText('费用统计暂不可用')

    def status_message(self, msg, timeout=5000):
        self.statusBar().showMessage(msg, timeout)
