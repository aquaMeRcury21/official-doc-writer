import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from utils.settings import ORG_CODE, ORG_NAME, ORG_SHORT, PLACE_NAME, WECHAT_ACCOUNT

# frozen 模式下使用 exe 目录，否则使用项目根目录
if getattr(sys, 'frozen', False):
    ENV_PATH = Path(sys.executable).resolve().parent / '.env'
else:
    ENV_PATH = Path(__file__).resolve().parent.parent.parent / '.env'


class SettingsWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel('设置')
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)
        layout.addSpacing(12)

        group1 = QGroupBox('单位信息')
        group1.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #e0e0e0;
                        border-radius: 6px; margin-top: 12px; padding: 20px 16px 16px; }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 8px; }
        """)
        f1 = QFormLayout(group1)
        f1.setSpacing(10)

        self.edit_org = QLineEdit()
        f1.addRow('单位全称:', self.edit_org)

        self.edit_short = QLineEdit()
        f1.addRow('发文机关简称:', self.edit_short)

        self.edit_code = QLineEdit()
        f1.addRow('发文机关代字:', self.edit_code)

        self.edit_place = QLineEdit()
        f1.addRow('地名:', self.edit_place)

        self.edit_wechat = QLineEdit()
        f1.addRow('公众号名称:', self.edit_wechat)
        layout.addWidget(group1)

        layout.addSpacing(12)

        group2 = QGroupBox('API 配置')
        group2.setStyleSheet(group1.styleSheet())
        f2 = QFormLayout(group2)
        f2.setSpacing(10)

        self.edit_api_key = QLineEdit()
        self.edit_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        f2.addRow('DeepSeek API Key:', self.edit_api_key)

        self.edit_base_url = QLineEdit()
        self.edit_base_url.setPlaceholderText('https://api.deepseek.com')
        f2.addRow('API Base URL:', self.edit_base_url)

        self.spin_budget = QSpinBox()
        self.spin_budget.setRange(1, 500)
        self.spin_budget.setSuffix(' 元/日')
        f2.addRow('每日预算:', self.spin_budget)
        layout.addWidget(group2)

        layout.addSpacing(12)

        group3 = QGroupBox('输出路径')
        group3.setStyleSheet(group2.styleSheet())
        f3 = QFormLayout(group3)
        f3.setSpacing(10)

        edit_output = QLabel(str(ENV_PATH.parent / 'output'))
        edit_output.setStyleSheet('color: #7f8c8d; font-size: 12px;')
        f3.addRow('output/', edit_output)

        edit_archive = QLabel(str(ENV_PATH.parent / 'knowledge-base' / 'archive'))
        edit_archive.setStyleSheet('color: #7f8c8d; font-size: 12px;')
        f3.addRow('archive/', edit_archive)
        layout.addWidget(group3)

        layout.addSpacing(16)

        btn_row = QHBoxLayout()
        self.btn_save = QPushButton('保存设置')
        self.btn_save.setObjectName('primaryBtn')
        self.btn_save.clicked.connect(self._save)
        self.btn_save.setMinimumWidth(120)
        btn_row.addWidget(self.btn_save)

        self.btn_reset = QPushButton('恢复默认')
        self.btn_reset.setObjectName('secondaryBtn')
        self.btn_reset.clicked.connect(self._load_settings)
        btn_row.addWidget(self.btn_reset)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def _load_settings(self):
        self.edit_org.setText(ORG_NAME)
        self.edit_short.setText(ORG_SHORT)
        self.edit_code.setText(ORG_CODE)
        self.edit_place.setText(PLACE_NAME)
        self.edit_wechat.setText(WECHAT_ACCOUNT)

        from os import getenv

        from dotenv import load_dotenv

        load_dotenv()
        self.edit_api_key.setText(getenv('DEEPSEEK_API_KEY', ''))
        self.edit_base_url.setText(getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'))

        try:
            from utils.cost_tracker import get_tracker

            tracker = get_tracker()
            self.spin_budget.setValue(int(tracker.daily_budget))
        except Exception:
            self.spin_budget.setValue(50)

    def _save(self):
        try:
            lines = []
            if ENV_PATH.exists():
                lines = ENV_PATH.read_text(encoding='utf-8').splitlines()
            else:
                lines = ['# 公文撰写工作站环境配置']

            api_key = self.edit_api_key.text().strip()
            base_url = self.edit_base_url.text().strip()

            new_vars = {}
            if api_key:
                new_vars['DEEPSEEK_API_KEY'] = api_key
            if base_url:
                new_vars['DEEPSEEK_BASE_URL'] = base_url

            existing_keys = set()
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if '=' in stripped and not stripped.startswith('#'):
                    key = stripped.split('=', 1)[0].strip()
                    existing_keys.add(key)
                    if key in new_vars:
                        new_lines.append(f'{key}={new_vars[key]}')
                        del new_vars[key]
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            for key, val in new_vars.items():
                new_lines.append(f'{key}={val}')

            ENV_PATH.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')

            import importlib

            from utils import settings

            importlib.reload(settings)

            QMessageBox.information(self, '保存成功', '设置已保存到 .env 文件\n部分设置重启后生效')
            self.main.status_message('设置已保存')
        except Exception as e:
            QMessageBox.critical(self, '保存失败', str(e))
