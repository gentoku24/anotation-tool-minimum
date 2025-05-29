import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QImage, QPixmap

import sys
import os

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ImageViewer(QWidget):
    """カメラ画像を表示するビューア"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # レイアウト設定
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        # 描画用の情報ラベル
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.info_label)
        
        # 画像データ
        self.image = None
        self.pixmap = None
        
        # 背景色を設定
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(30, 30, 30))
        self.setPalette(palette)
        
        # サイズポリシー
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def paintEvent(self, event):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景を描画
        painter.fillRect(event.rect(), QColor(30, 30, 30))
        
        if self.pixmap is None or self.pixmap.isNull():
            # 画像がない場合はメッセージを表示
            painter.setPen(QPen(Qt.white))
            font = QFont()
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(event.rect(), Qt.AlignCenter, "No image data\nPlease load point cloud with camera image")
            return
        
        try:
            # 画像を表示領域に合わせて描画
            # 横長の画像は高さに合わせてスケーリング、縦長の画像は幅に合わせてスケーリング
            image_ratio = self.pixmap.width() / self.pixmap.height() if self.pixmap.height() > 0 else 1.0
            view_ratio = self.width() / self.height() if self.height() > 0 else 1.0
            
            scaled_pixmap = None
            if image_ratio > view_ratio:
                # 横長の画像はウィンドウの幅に合わせる
                scaled_width = self.width()
                scaled_height = int(scaled_width / image_ratio)
                scaled_pixmap = self.pixmap.scaled(
                    scaled_width, 
                    scaled_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            else:
                # 縦長の画像はウィンドウの高さに合わせる
                scaled_height = self.height()
                scaled_width = int(scaled_height * image_ratio)
                scaled_pixmap = self.pixmap.scaled(
                    scaled_width,
                    scaled_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            
            # スケーリング結果の確認
            if scaled_pixmap.isNull():
                # 失敗した場合は元のピクスマップを使用
                scaled_pixmap = self.pixmap
            
            # 画像を中央に配置
            x = (self.width() - scaled_pixmap.width()) // 2
            y = (self.height() - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x, y, scaled_pixmap)
            
            # 情報表示
            painter.setPen(QPen(Qt.white))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            
            if self.image and not self.image.isNull():
                painter.drawText(10, 20, f"Image: {self.image.width()}x{self.image.height()}")
        
        except Exception as e:
            # 例外が発生した場合はエラーメッセージを表示
            painter.setPen(QPen(Qt.red))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(event.rect(), Qt.AlignCenter, f"Error displaying image:\n{str(e)}")
    
    def load_image(self, image: QImage) -> bool:
        """画像をロード"""
        if image is None or image.isNull():
            return False
        
        self.image = image
        self.pixmap = QPixmap.fromImage(image)
        
        if self.pixmap.isNull():
            return False
            
        self.update()  # 再描画
        return True
    
    def clear(self):
        """表示をクリア"""
        self.image = None
        self.pixmap = None
        self.update()  # 再描画 