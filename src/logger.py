import logging
import os
from datetime import datetime
from typing import Optional

class Logger:
    def __init__(self, log_dir: str = "logs"):
        """ロガーの初期化"""
        # プロジェクトのルートディレクトリを取得
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(self.project_root, log_dir)
        self._setup_log_directory()
        self._setup_loggers()

    def _setup_log_directory(self):
        """ログディレクトリの作成"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _setup_loggers(self):
        """ロガーの設定"""
        # エラーログの設定
        self.error_logger = logging.getLogger('error_logger')
        self.error_logger.setLevel(logging.ERROR)
        error_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'error_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.error_logger.addHandler(error_handler)

        # 変更ログの設定
        self.change_logger = logging.getLogger('change_logger')
        self.change_logger.setLevel(logging.INFO)
        change_handler = logging.FileHandler(
            os.path.join(self.log_dir, f'change_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
        change_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        self.change_logger.addHandler(change_handler)

    def log_error(self, message: str, error: Optional[Exception] = None):
        """エラーログを記録"""
        if error:
            self.error_logger.error(f"{message}: {str(error)}")
        else:
            self.error_logger.error(message)

    def log_change(self, message: str):
        """変更ログを記録"""
        self.change_logger.info(message)

# グローバルなロガーインスタンス
logger = Logger() 