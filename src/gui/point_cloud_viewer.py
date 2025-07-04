import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont

import sys
import os
import math
from typing import Optional

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import BoundingBox3D, ClassLabel

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
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.info_label)
        
        # 点群データ
        self.point_cloud_xyz = None
        self.transformed_points = None
        
        # アノテーションデータ
        self.bounding_boxes = {}  # id -> BoundingBox3D
        self.transformed_boxes = {}  # id -> 変換後の頂点座標リスト
        
        # 選択状態
        self.selected_box_id = None
        
        # 背景色を設定
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(50, 50, 50))
        self.setPalette(palette)
        
        # サイズポリシー
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 2D表示用のスケール・オフセット（平行移動）
        self.scale = 1.0
        self.offset = QPointF(0, 0)
        self.last_mouse_pos = None
        self.is_panning = False
        self.is_rotating = False
        
        # 回転角度（ラジアン）
        self.rotation_x = 0.0  # X軸周りの回転
        self.rotation_y = 0.0  # Y軸周りの回転
        self.rotation_z = 0.0  # Z軸周りの回転
        
        # マウス操作の感度
        self.rotation_sensitivity = 0.01
        
        # 現在の回転行列
        self.current_rotation_matrix = np.eye(3)

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
            painter.drawText(event.rect(), Qt.AlignCenter, "No point cloud data\nPlease load data using 'Open Point Cloud' button")
            return
        
        # 点群の数を表示
        painter.setPen(QPen(Qt.white))
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(10, 20, f"Point Cloud: {len(self.point_cloud_xyz)} points")
        painter.drawText(10, 40, f"Rotation: X={math.degrees(self.rotation_x):.1f}°, Y={math.degrees(self.rotation_y):.1f}°, Z={math.degrees(self.rotation_z):.1f}°")
        
        if self.transformed_points is not None:
            points = self.transformed_points
            if len(points) > 0:
                # 点群の中心をウィンドウ中央に合わせる
                min_xy = np.min(points[:, :2], axis=0)
                max_xy = np.max(points[:, :2], axis=0)
                center_xy = (min_xy + max_xy) / 2
                widget_center = QPointF(self.width() / 2, self.height() / 2)
                
                # スケール自動調整（ウィンドウに収まるように）
                range_xy = max(max_xy - min_xy)
                if range_xy > 0:
                    scale = 0.8 * min(self.width(), self.height()) / range_xy
                else:
                    scale = 1.0
                scale *= self.scale
                
                # 点を描画
                painter.setPen(QPen(Qt.green, 2))
                for pt in points:
                    x, y = pt[0], pt[1]
                    # 2D座標変換
                    screen_x = (x - center_xy[0]) * scale + widget_center.x() + self.offset.x()
                    screen_y = (y - center_xy[1]) * scale + widget_center.y() + self.offset.y()
                    painter.drawPoint(int(screen_x), int(screen_y))
                
                # バウンディングボックスを描画
                for bbox_id, box_vertices in self.transformed_boxes.items():
                    bbox = self.bounding_boxes[bbox_id]
                    color = QColor(*bbox.class_color)
                    
                    # 選択状態に応じてペンを設定
                    if bbox_id == self.selected_box_id:
                        painter.setPen(QPen(color, 2, Qt.SolidLine))
                    else:
                        painter.setPen(QPen(color, 1, Qt.SolidLine))
                    
                    # 頂点を2D座標に変換
                    screen_vertices = []
                    for vertex in box_vertices:
                        screen_x = (vertex[0] - center_xy[0]) * scale + widget_center.x() + self.offset.x()
                        screen_y = (vertex[1] - center_xy[1]) * scale + widget_center.y() + self.offset.y()
                        screen_vertices.append((int(screen_x), int(screen_y)))
                    
                    # 各辺を描画（立方体の12本の辺）
                    # 底面の4辺
                    for i in range(4):
                        painter.drawLine(screen_vertices[i][0], screen_vertices[i][1], 
                                        screen_vertices[(i+1)%4][0], screen_vertices[(i+1)%4][1])
                    
                    # 上面の4辺
                    for i in range(4):
                        painter.drawLine(screen_vertices[i+4][0], screen_vertices[i+4][1], 
                                        screen_vertices[(i+1)%4+4][0], screen_vertices[(i+1)%4+4][1])
                    
                    # 側面の4辺
                    for i in range(4):
                        painter.drawLine(screen_vertices[i][0], screen_vertices[i][1], 
                                        screen_vertices[i+4][0], screen_vertices[i+4][1])
        
        # バウンディングボックス情報
        self.paint_overlay(painter)

    def paint_overlay(self, painter: QPainter, event=None):
        """オーバーレイの描画"""
        # バウンディングボックス情報
        y_pos = 60
        for bbox_id, bbox in self.bounding_boxes.items():
            color = QColor(*bbox.class_color)
            is_selected = bbox_id == self.selected_box_id
            
            if is_selected:
                # 選択中のバウンディングボックスは明るく表示
                text = f"> {bbox.class_label} ({bbox_id[:8]}...): {bbox.center}"
                color = color.lighter(130)  # 明るくする
            else:
                text = f"  {bbox.class_label} ({bbox_id[:8]}...): {bbox.center}"
            
            painter.setPen(QPen(color, 2))
            painter.drawText(10, y_pos, text)
            y_pos += 20

    def apply_rotation(self):
        """回転を適用して点群を変換"""
        if self.point_cloud_xyz is None:
            return
        
        # 回転行列を計算
        # X軸周りの回転
        rx_matrix = np.array([
            [1, 0, 0],
            [0, np.cos(self.rotation_x), -np.sin(self.rotation_x)],
            [0, np.sin(self.rotation_x), np.cos(self.rotation_x)]
        ])
        
        # Y軸周りの回転
        ry_matrix = np.array([
            [np.cos(self.rotation_y), 0, np.sin(self.rotation_y)],
            [0, 1, 0],
            [-np.sin(self.rotation_y), 0, np.cos(self.rotation_y)]
        ])
        
        # Z軸周りの回転
        rz_matrix = np.array([
            [np.cos(self.rotation_z), -np.sin(self.rotation_z), 0],
            [np.sin(self.rotation_z), np.cos(self.rotation_z), 0],
            [0, 0, 1]
        ])
        
        # 回転行列を合成（Z→Y→Xの順に適用）
        self.current_rotation_matrix = rx_matrix @ ry_matrix @ rz_matrix
        
        # 点群に回転を適用
        self.transformed_points = self.point_cloud_xyz @ self.current_rotation_matrix.T
        
        # バウンディングボックスにも回転を適用
        self.transform_bounding_boxes()
        
        # 再描画
        self.update()

    def transform_bounding_boxes(self):
        """すべてのバウンディングボックスに変換を適用"""
        self.transformed_boxes = {}
        
        for bbox_id, bbox in self.bounding_boxes.items():
            # バウンディングボックスの8つの頂点を計算
            center = np.array(bbox.center)
            size = np.array(bbox.size)
            rotation = np.array(bbox.rotation)
            
            # バウンディングボックスの点を変換
            transformed_points = self._transform_bbox_points(center, size, rotation)
            
            # 変換した頂点を保存
            self.transformed_boxes[bbox_id] = transformed_points

    def _transform_bbox_points(self, center, size, rotation):
        # バウンディングボックスのローカル回転行列を作成
        # X軸周りの回転
        rx_matrix = np.array([
            [1, 0, 0],
            [0, np.cos(rotation[0]), -np.sin(rotation[0])],
            [0, np.sin(rotation[0]), np.cos(rotation[0])]
        ])
        
        # Y軸周りの回転
        ry_matrix = np.array([
            [np.cos(rotation[1]), 0, np.sin(rotation[1])],
            [0, 1, 0],
            [-np.sin(rotation[1]), 0, np.cos(rotation[1])]
        ])
        
        # Z軸周りの回転
        rz_matrix = np.array([
            [np.cos(rotation[2]), -np.sin(rotation[2]), 0],
            [np.sin(rotation[2]), np.cos(rotation[2]), 0],
            [0, 0, 1]
        ])
        
        # 回転行列を合成（Z→Y→Xの順に適用）
        rotation_matrix = rx_matrix @ ry_matrix @ rz_matrix
        
        # 頂点の順序を明示的に定義（立方体の8つの頂点）
        # 順序: [左下前, 右下前, 右上前, 左上前, 左下後, 右下後, 右上後, 左上後]
        corners = [
            [-1, -1, -1],  # 左下前
            [1, -1, -1],   # 右下前
            [1, 1, -1],    # 右上前
            [-1, 1, -1],   # 左上前
            [-1, -1, 1],   # 左下後
            [1, -1, 1],    # 右下後
            [1, 1, 1],     # 右上後
            [-1, 1, 1]     # 左上後
        ]
        
        # 8つの頂点の座標を計算（回転を含む）
        vertices = []
        for corner in corners:
            # サイズに合わせて拡大
            local_offset = np.array([corner[0] * size[0], corner[1] * size[1], corner[2] * size[2]])
            # ボックスの回転を適用
            rotated_offset = local_offset @ rotation_matrix.T
            # 中心位置を加算
            vertices.append(center + rotated_offset)
        
        # ビューワーの回転を適用
        transformed_vertices = np.array(vertices) @ self.current_rotation_matrix.T
        
        return transformed_vertices

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_panning = True
            self.is_rotating = False
            self.last_mouse_pos = event.pos()
        elif event.button() == Qt.RightButton:
            self.is_rotating = True
            self.is_panning = False
            self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_mouse_pos is None:
            return
            
        if self.is_panning:
            # 平行移動
            delta = event.pos() - self.last_mouse_pos
            self.offset += delta
            self.last_mouse_pos = event.pos()
            self.update()
        elif self.is_rotating:
            # 回転
            delta = event.pos() - self.last_mouse_pos
            
            # SHIFTキーが押されている場合はZ軸周り回転
            modifiers = event.modifiers()
            if modifiers & Qt.ShiftModifier:
                # X移動をZ回転に割り当て
                self.rotation_z += delta.x() * self.rotation_sensitivity
            else:
                # 通常の回転: マウスのX移動→Y軸周り回転、Y移動→X軸周り回転
                self.rotation_y += delta.x() * self.rotation_sensitivity
                self.rotation_x += delta.y() * self.rotation_sensitivity
                
            self.last_mouse_pos = event.pos()
            self.apply_rotation()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_panning = False
            self.last_mouse_pos = None
        elif event.button() == Qt.RightButton:
            self.is_rotating = False
            self.last_mouse_pos = None

    def wheelEvent(self, event):
        # マウスホイールで拡大縮小
        angle = event.angleDelta().y()
        factor = 1.15 if angle > 0 else 0.85
        self.scale *= factor
        self.update()

    def load_point_cloud(self, _, xyz):
        """点群データを読み込む"""
        if xyz is None:
            return False
        self.point_cloud_xyz = xyz
        self.transformed_points = xyz.copy()  # 初期状態では変換なし
        self.update()
        return True

    def add_bounding_box(self, bbox: BoundingBox3D) -> bool:
        """バウンディングボックスを追加"""
        try:
            # 保存
            self.bounding_boxes[bbox.id] = bbox
            
            # 変換を適用
            self.transform_bounding_boxes()
            
            # 再描画
            self.update()
            return True
        except Exception as e:
            return False

    def remove_bounding_box(self, bbox_id: str) -> bool:
        """バウンディングボックスを削除"""
        if bbox_id not in self.bounding_boxes:
            return False
        
        try:
            # 管理リストから削除
            del self.bounding_boxes[bbox_id]
            if bbox_id in self.transformed_boxes:
                del self.transformed_boxes[bbox_id]
                
            # 選択状態をクリア
            if self.selected_box_id == bbox_id:
                self.selected_box_id = None
                
            # 再描画
            self.update()
            return True
        except Exception as e:
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
        self.transformed_boxes = {}
        
        # 選択状態をクリア
        self.selected_box_id = None
        
        # 再描画
        self.update()
    
    def get_bbox(self, bbox_id: str) -> Optional[BoundingBox3D]:
        """指定IDのバウンディングボックスを取得"""
        if bbox_id in self.bounding_boxes:
            return self.bounding_boxes[bbox_id]
        return None
    
    def update_bounding_box(self, bbox: BoundingBox3D) -> bool:
        """バウンディングボックスを更新"""
        result = self.add_bounding_box(bbox)  # add_bounding_boxは既存のIDなら更新処理も行う
        self.transform_bounding_boxes()  # 変換を適用
        return result
    
    def close_viewer(self):
        """ビューアを閉じる"""
        pass  # 特別な終了処理は不要

    def set_selected_box(self, box_id):
        """特定のバウンディングボックスを選択状態にする"""
        self.selected_box_id = box_id
        self.update()
    
    def has_selected_box(self):
        """選択中のバウンディングボックスがあるか確認"""
        return self.selected_box_id is not None
    
    def get_selected_box_id(self):
        """選択中のバウンディングボックスのIDを取得"""
        return self.selected_box_id
    
    def get_camera_position(self):
        """カメラの位置を取得（現在の回転状態を考慮）"""
        # 基本的なカメラ位置（回転前）
        base_pos = np.array([0.0, 0.0, 5.0])
        
        # 回転行列の逆行列を計算
        inv_rotation = np.linalg.inv(self.current_rotation_matrix)
        
        # 回転を適用
        rotated_pos = base_pos @ inv_rotation
        
        return rotated_pos
    
    def get_camera_direction(self):
        """カメラの方向ベクトルを取得（現在の回転状態を考慮）"""
        # 基本的な視線方向（Z軸の負方向）
        base_dir = np.array([0.0, 0.0, -1.0])
        
        # 回転行列の逆行列を計算
        inv_rotation = np.linalg.inv(self.current_rotation_matrix)
        
        # 回転を適用
        rotated_dir = base_dir @ inv_rotation
        
        # 単位ベクトル化
        norm = np.linalg.norm(rotated_dir)
        if norm > 0:
            rotated_dir = rotated_dir / norm
        
        return rotated_dir