#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.gui.main_window import MainWindow
from PySide6.QtWidgets import QApplication

def main():
    """アプリケーションのメインエントリポイント"""
    # アプリケーションの作成
    app = QApplication(sys.argv)
    app.setApplicationName("3Dアノテーションツール")
    
    # 必要なディレクトリが存在することを確認
    os.makedirs("data", exist_ok=True)
    os.makedirs("class_labels", exist_ok=True)
    
    # メインウィンドウの作成と表示
    window = MainWindow()
    window.show()
    
    # イベントループを開始
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 