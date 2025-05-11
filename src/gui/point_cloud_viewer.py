import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont

import sys
import os

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import BoundingBox3D, ClassLabel

class PointCloudViewer(QWidget):
    # シグナル定義
    box_selected = Signal(str)  # 選択されたボックスのID
    box_created = Signal(BoundingBox3D)  # 新規作成されたボックス
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # レイアウト設定
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        # 描画用の情報ラベル
        self.info_label = QLabel("点群データと3Dバウンディングボックスの描画領域")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.info_label)
        
        # 点群データ
        self.point_cloud_xyz = None
        
        # アノテーションデータ
        self.bounding_boxes = {}  # id -> BoundingBox3D
        
        # 選択状態
        self.selected_box_id = None
        
        # 背景色を設定
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(50, 50, 50))
        self.setPalette(palette)
        
        # サイズポリシー
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def paintEvent(self, event):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景を描画
        painter.fillRect(event.rect(), QColor(50, 50, 50))
        
        if self.point_cloud_xyz is None:
            # 点群がない場合はメッセージを表示
            painter.setPen(QPen(Qt.white))
            font = QFont()
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(event.rect(), Qt.AlignCenter, "点群データがありません\n「点群を開く」ボタンからデータを読み込んでください")
            return
        
        # 点群の数を表示
        painter.setPen(QPen(Qt.white))
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(10, 20, f"点群データ: {len(self.point_cloud_xyz)}点")
        
        # バウンディングボックス情報
        y_pos = 40
        for bbox_id, bbox in self.bounding_boxes.items():
            color = QColor(*bbox.class_color)
            is_selected = bbox_id == self.selected_box_id
            
            if is_selected:
                # 選択されたボックスは太字で
                painter.setPen(QPen(color, 2))
                font.setBold(True)
            else:
                painter.setPen(QPen(color))
                font.setBold(False)
            
            painter.setFont(font)
            painter.drawText(10, y_pos, f"{bbox.class_label}: {bbox.center} サイズ: {bbox.size}")
            y_pos += 20
    
    def load_point_cloud(self, _, xyz):
        """点群データを読み込む"""
        if xyz is None:
            return False
        
        # 点群データを設定
        self.point_cloud_xyz = xyz
        
        # 再描画
        self.update()
        
        return True
    
    def add_bounding_box(self, bbox: BoundingBox3D) -> bool:
        """バウンディングボックスを追加"""
        try:
            # 保存
            self.bounding_boxes[bbox.id] = bbox
            
            # 再描画
            self.update()
            return True
        except Exception as e:
            print(f"バウンディングボックス追加エラー: {e}")
            return False
    
    def remove_bounding_box(self, bbox_id: str) -> bool:
        """バウンディングボックスを削除"""
        if bbox_id not in self.bounding_boxes:
            return False
        
        try:
            # 管理リストから削除
            del self.bounding_boxes[bbox_id]
            
            # 選択状態をクリア
            if self.selected_box_id == bbox_id:
                self.selected_box_id = None
            
            # 再描画
            self.update()
            return True
        except Exception as e:
            print(f"バウンディングボックス削除エラー: {e}")
            return False
    
    def select_bounding_box(self, bbox_id: str) -> bool:
        """バウンディングボックスを選択"""
        if bbox_id not in self.bounding_boxes:
            return False
        
        # 選択状態を更新
        self.selected_box_id = bbox_id
        
        # 選択シグナルを発行
        self.box_selected.emit(bbox_id)
        
        # 再描画
        self.update()
        return True
    
    def clear_all_bounding_boxes(self):
        """全てのバウンディングボックスをクリア"""
        # 管理リストをクリア
        self.bounding_boxes = {}
        
        # 選択状態をクリア
        self.selected_box_id = None
        
        # 再描画
        self.update()
    
    def get_bounding_box(self, bbox_id: str) -> BoundingBox3D:
        """指定IDのバウンディングボックスを取得"""
        if bbox_id in self.bounding_boxes:
            return self.bounding_boxes[bbox_id]
        return None
    
    def update_bounding_box(self, bbox: BoundingBox3D) -> bool:
        """バウンディングボックスを更新"""
        return self.add_bounding_box(bbox)  # add_bounding_boxは既存のIDなら更新処理も行う
    
    def close_viewer(self):
        """ビューアを閉じる"""
        pass  # 特別な終了処理は不要