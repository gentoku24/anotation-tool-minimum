#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# 自分自身のディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

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