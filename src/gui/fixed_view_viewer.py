import numpy as np
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPen, QFont, QPainter
from PySide6.QtWidgets import QLabel
from enum import Enum

from .point_cloud_viewer import PointCloudViewer

class ViewType(Enum):
    """ビューの種類を定義する列挙型"""
    TOP = 1      # 上からの視点
    FRONT = 2    # 正面からの視点
    SIDE = 3     # 横からの視点

class FixedViewViewer(PointCloudViewer):
    """特定の視点からバウンディングボックスを表示するビューア"""
    
    def __init__(self, view_type, parent=None):
        """初期化
        
        Args:
            view_type (ViewType): ビューの種類（TOP, FRONT, SIDE）
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.view_type = view_type
        self.focused_box_id = None
        
        # 視点タイプに応じたラベルを設定
        if view_type == ViewType.TOP:
            self.info_label.setText("")
        elif view_type == ViewType.FRONT:
            self.info_label.setText("")
        elif view_type == ViewType.SIDE:
            self.info_label.setText("")
        
        # 視点の距離設定（メートル単位）
        self.view_distance = {
            ViewType.TOP: 5.0,    # 上面ビュー
            ViewType.FRONT: 15.0,  # 正面ビュー
            ViewType.SIDE: 5.0    # 側面ビュー
        }
        
        # 初期スケール設定
        self.initial_scale = {
            ViewType.TOP: 1.0,    # 上面ビュー
            ViewType.FRONT: 0.5,  # 正面ビュー
            ViewType.SIDE: 0.8    # 側面ビュー
        }
        
        # 初期スケールを設定
        self.scale = self.initial_scale[self.view_type]
        
        # マウス操作を制限（ズームのみ許可）
        self.setMouseTracking(False)
        
        # 基本的な視点を設定
        self._set_initial_rotation()
    
    def _set_initial_rotation(self):
        """視点タイプに応じた初期回転を設定"""
        if self.view_type == ViewType.TOP:
            # 上面ビュー（X軸周りに90度回転）
            self.rotation_x = -np.pi/2
            self.rotation_y = 0
            self.rotation_z = 0
        elif self.view_type == ViewType.FRONT:
            # 正面ビュー
            self.rotation_x = 0
            self.rotation_y = 0
            self.rotation_z = 0
        elif self.view_type == ViewType.SIDE:
            # 側面ビュー（Y軸周りに90度回転）
            self.rotation_x = 0
            self.rotation_y = np.pi/2
            self.rotation_z = 0
        
        # 回転を適用
        self.apply_rotation()
    
    def mousePressEvent(self, event):
        """マウス押下イベント（オーバーライドして制限する）"""
        # すべてのマウス操作を無効化
        event.accept()
    
    def mouseMoveEvent(self, event):
        """マウス移動イベント（オーバーライドして制限する）"""
        event.accept()
    
    def focus_on_box(self, bbox_id):
        """指定されたバウンディングボックスにフォーカスする
        
        Args:
            bbox_id (str): フォーカスするバウンディングボックスのID
        """
        if bbox_id not in self.bounding_boxes:
            return False
        
        self.focused_box_id = bbox_id
        
        # 再描画
        self.update()
        return True
    
    def paintEvent(self, event):
        """描画イベント（オーバーライド）"""
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
        
        # 視点タイプをラベルに表示
        view_type_text = {
            ViewType.TOP: "上面ビュー (Top View)",
            ViewType.FRONT: "正面ビュー (Front View)",
            ViewType.SIDE: "側面ビュー (Side View)"
        }.get(self.view_type, "")
        
        # 点群の数と視点情報を表示
        painter.setPen(QPen(Qt.white))
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(10, 20, f"{view_type_text}")
        painter.drawText(10, 40, f"点群データ: {len(self.point_cloud_xyz)}点")
        
        # 選択されているボックス情報の表示
        if self.focused_box_id and self.focused_box_id in self.bounding_boxes:
            bbox = self.bounding_boxes[self.focused_box_id]
            painter.drawText(10, 60, f"フォーカス: {bbox.class_label}")
        
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
                    # 視点タイプに応じたスケール係数を適用
                    auto_scale = 0.6 * min(self.width(), self.height()) / range_xy
                    # 視点タイプに基づく係数を適用
                    view_scale_factor = {
                        ViewType.TOP: 1.0,
                        ViewType.FRONT: 0.5,  # 正面ビューは縮小表示
                        ViewType.SIDE: 0.8
                    }[self.view_type]
                    
                    auto_scale *= view_scale_factor
                else:
                    auto_scale = self.initial_scale[self.view_type]
                
                # ユーザーのズーム操作を反映したスケール
                scale = auto_scale * self.scale
                
                # 選択されたボックスが中心になるようにオフセットを調整
                camera_offset = QPointF(0, 0)
                if self.focused_box_id and self.focused_box_id in self.transformed_boxes:
                    # 選択されたボックスの中心を計算
                    bbox_vertices = self.transformed_boxes[self.focused_box_id]
                    bbox_center = np.mean(bbox_vertices, axis=0)
                    # ボックス中心を画面中央に配置するためのオフセット計算
                    screen_x = (bbox_center[0] - center_xy[0]) * scale + widget_center.x()
                    screen_y = (bbox_center[1] - center_xy[1]) * scale + widget_center.y()
                    camera_offset = QPointF(widget_center.x() - screen_x, widget_center.y() - screen_y)
                
                # 最終的なオフセットを計算（カメラオフセット + ユーザー調整オフセット）
                final_offset = self.offset + camera_offset
                
                # 点を描画
                painter.setPen(QPen(Qt.green, 2))
                for pt in points:
                    x, y = pt[0], pt[1]
                    # 2D座標変換
                    screen_x = (x - center_xy[0]) * scale + widget_center.x() + final_offset.x()
                    screen_y = (y - center_xy[1]) * scale + widget_center.y() + final_offset.y()
                    painter.drawPoint(int(screen_x), int(screen_y))
                
                # バウンディングボックスを描画
                for bbox_id, box_vertices in self.transformed_boxes.items():
                    bbox = self.bounding_boxes[bbox_id]
                    color = QColor(*bbox.class_color)
                    
                    # 選択状態に応じてペンを設定（フォーカスされたボックスは太い線で）
                    if bbox_id == self.focused_box_id:
                        painter.setPen(QPen(color, 3, Qt.SolidLine))
                    elif bbox_id == self.selected_box_id:
                        painter.setPen(QPen(color, 2, Qt.SolidLine))
                    else:
                        painter.setPen(QPen(color, 1, Qt.SolidLine))
                    
                    # 頂点を2D座標に変換
                    screen_vertices = []
                    for vertex in box_vertices:
                        screen_x = (vertex[0] - center_xy[0]) * scale + widget_center.x() + final_offset.x()
                        screen_y = (vertex[1] - center_xy[1]) * scale + widget_center.y() + final_offset.y()
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

    def _adjust_view_to_bbox(self):
        """選択されたバウンディングボックスに合わせて視点を調整"""
        if not self.focused_box_id or self.focused_box_id not in self.bounding_boxes:
            return
        
        # 選択されたボックス
        bbox = self.bounding_boxes[self.focused_box_id]
        
        # ボックスの位置と大きさを取得
        center = np.array(bbox.center)
        size = np.array(bbox.size)
        
        # ボックスの回転角度をラジアンに変換
        box_rotation = np.array(bbox.rotation) * (np.pi / 180.0)
        
        # 視点タイプに応じた回転と位置の調整
        if self.view_type == ViewType.TOP:
            # 上面ビュー（ボックスの上から見る）
            self.rotation_x = -np.pi/2  # X軸回りに-90度回転
            self.rotation_y = box_rotation[1]  # ボックスのY軸回転に合わせる
            self.rotation_z = box_rotation[2]  # ボックスのZ軸回転に合わせる
            
            # 視点の調整（ボックス上部から距離を取る）
            view_distance = self.view_distance[ViewType.TOP]
            # オフセットの計算は実際の描画時に行います
            
        elif self.view_type == ViewType.FRONT:
            # 正面ビュー（ボックスの前から見る）
            self.rotation_x = box_rotation[0]  # ボックスのX軸回転に合わせる
            self.rotation_y = box_rotation[1]  # ボックスのY軸回転に合わせる
            self.rotation_z = box_rotation[2]  # ボックスのZ軸回転に合わせる
            
            # 視点の調整（ボックス正面から距離を取る）
            view_distance = self.view_distance[ViewType.FRONT]
            # オフセットの計算は実際の描画時に行います
            
        elif self.view_type == ViewType.SIDE:
            # 側面ビュー（ボックスの横から見る）
            self.rotation_x = box_rotation[0]  # ボックスのX軸回転に合わせる
            self.rotation_y = np.pi/2 + box_rotation[1]  # Y軸回りに90度 + ボックスのY軸回転
            self.rotation_z = box_rotation[2]  # ボックスのZ軸回転に合わせる
            
            # 視点の調整（ボックス側面から距離を取る）
            view_distance = self.view_distance[ViewType.SIDE]
            # オフセットの計算は実際の描画時に行います
        
        # 回転を適用
        self.apply_rotation()
        
        # 適切なスケールを設定（ボックスサイズに基づく）
        max_dimension = max(size)
        if max_dimension > 0:
            # ボックスが画面の約60%を占めるようなスケールに設定
            self.scale = 0.6 * min(self.width(), self.height()) / max_dimension
        else:
            self.scale = 1.0
        
        # 初期オフセットはゼロに設定（実際の描画時に調整）
        self.offset = QPointF(0, 0)
    
    def sync_from_main_viewer(self, main_viewer):
        """メインビューアからデータを同期する
        
        Args:
            main_viewer (PointCloudViewer): 同期元のメインビューア
        """
        # 点群データをコピー
        self.point_cloud_xyz = main_viewer.point_cloud_xyz
        if self.point_cloud_xyz is not None:
            self.transformed_points = self.point_cloud_xyz.copy()
        else:
            # 点群データがない場合は処理終了
            return
        
        # バウンディングボックスをコピー
        self.bounding_boxes = {}
        for bbox_id, bbox in main_viewer.bounding_boxes.items():
            self.bounding_boxes[bbox_id] = bbox
        
        # メインビューアから回転状態をコピー（これにより視点の一貫性を保持）
        # self.rotation_x = main_viewer.rotation_x
        # self.rotation_y = main_viewer.rotation_y
        # self.rotation_z = main_viewer.rotation_z
        
        # 選択状態を同期
        self.selected_box_id = main_viewer.selected_box_id
        
        # フォーカス対象のボックスを設定
        if self.selected_box_id:
            self.focused_box_id = self.selected_box_id
            # 選択されたボックスを中心に視点を調整
            self._adjust_view_to_bbox()
        else:
            # 選択がない場合は初期視点に戻す
            self._set_initial_rotation()
            # デフォルトのオフセットとスケールを設定
            self.offset = QPointF(0, 0)
            self.scale = self.initial_scale[self.view_type]
        
        # 回転と変換を複数回適用して確実に反映
        for _ in range(2):  # 2回適用することで確実に反映
            self.apply_rotation()  # まず回転を適用してから
            self.transform_bounding_boxes()  # バウンディングボックスの変換を実行
        
        # 強制的に再描画
        self.update() 