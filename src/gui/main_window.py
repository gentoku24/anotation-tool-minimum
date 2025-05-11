import os
import sys
import json
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QComboBox, QListWidget,
    QListWidgetItem, QMessageBox, QGroupBox, QFormLayout, QDoubleSpinBox,
    QStatusBar, QToolBar
)
from PySide6.QtCore import Qt, Slot, QDir
from PySide6.QtGui import QIcon, QKeySequence, QAction

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import BoundingBox3D, ClassLabel, AnnotationManager, ClassManager
from src.utils import load_point_cloud
from gui.point_cloud_viewer import PointCloudViewer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # ウィンドウ設定
        self.setWindowTitle("3Dアノテーションツール")
        self.setMinimumSize(1200, 800)
        
        # データ管理
        self.current_file_path = None
        self.annotation_manager = AnnotationManager()
        self.class_manager = ClassManager()
        self.point_cloud = None
        self.point_cloud_xyz = None
        
        # クラスラベルの読み込み
        self._load_class_labels()
        
        # UIの初期化
        self._init_ui()
    
    def _init_ui(self):
        """UIコンポーネントの初期化"""
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(central_widget)
        
        # ツールバー
        self._create_toolbar()
        
        # メインコンテンツのスプリッター
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左側のコントロールパネル
        control_panel = self._create_control_panel()
        splitter.addWidget(control_panel)
        
        # 右側の点群ビューアー
        self.point_cloud_viewer = PointCloudViewer()
        self.point_cloud_viewer.box_selected.connect(self._on_bbox_selected)
        self.point_cloud_viewer.box_created.connect(self._on_bbox_created)
        splitter.addWidget(self.point_cloud_viewer)
        
        # スプリッターの初期サイズ比率設定
        splitter.setSizes([300, 900])
        
        # ステータスバー
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("準備完了")
    
    def _create_toolbar(self):
        """ツールバーの作成"""
        toolbar = QToolBar("メインツールバー")
        self.addToolBar(toolbar)
        
        # ファイル操作
        open_action = QAction("点群を開く", self)
        open_action.triggered.connect(self._open_point_cloud)
        toolbar.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self._save_annotation)
        toolbar.addAction(save_action)
        
        # 編集操作
        toolbar.addSeparator()
        
        undo_action = QAction("元に戻す", self)
        undo_action.triggered.connect(self._undo)
        undo_action.setShortcut(QKeySequence.Undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction("やり直し", self)
        redo_action.triggered.connect(self._redo)
        redo_action.setShortcut(QKeySequence.Redo)
        toolbar.addAction(redo_action)
        
        # アノテーション操作
        toolbar.addSeparator()
        
        add_box_action = QAction("ボックス追加", self)
        add_box_action.triggered.connect(self._add_new_box)
        toolbar.addAction(add_box_action)
        
        delete_box_action = QAction("削除", self)
        delete_box_action.triggered.connect(self._delete_selected_box)
        toolbar.addAction(delete_box_action)
    
    def _create_control_panel(self):
        """コントロールパネルの作成"""
        control_panel = QWidget()
        layout = QVBoxLayout(control_panel)
        
        # 1. アノテーションリスト
        annotation_group = QGroupBox("アノテーションリスト")
        annotation_layout = QVBoxLayout()
        
        self.annotation_list = QListWidget()
        self.annotation_list.itemClicked.connect(self._on_annotation_item_clicked)
        annotation_layout.addWidget(self.annotation_list)
        
        annotation_buttons_layout = QHBoxLayout()
        add_button = QPushButton("追加")
        add_button.clicked.connect(self._add_new_box)
        delete_button = QPushButton("削除")
        delete_button.clicked.connect(self._delete_selected_box)
        annotation_buttons_layout.addWidget(add_button)
        annotation_buttons_layout.addWidget(delete_button)
        annotation_layout.addLayout(annotation_buttons_layout)
        
        annotation_group.setLayout(annotation_layout)
        layout.addWidget(annotation_group)
        
        # 2. 選択されたボックスのプロパティ
        properties_group = QGroupBox("プロパティ")
        properties_layout = QFormLayout()
        
        # クラス選択
        self.class_combo = QComboBox()
        self._update_class_combo()
        properties_layout.addRow("クラス:", self.class_combo)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        
        # 寸法と位置の編集
        position_group = QGroupBox("位置")
        position_layout = QFormLayout()
        
        self.pos_x = QDoubleSpinBox()
        self.pos_x.setRange(-1000, 1000)
        self.pos_x.setSingleStep(0.1)
        self.pos_x.valueChanged.connect(lambda: self._update_bbox_property("center", 0))
        position_layout.addRow("X:", self.pos_x)
        
        self.pos_y = QDoubleSpinBox()
        self.pos_y.setRange(-1000, 1000)
        self.pos_y.setSingleStep(0.1)
        self.pos_y.valueChanged.connect(lambda: self._update_bbox_property("center", 1))
        position_layout.addRow("Y:", self.pos_y)
        
        self.pos_z = QDoubleSpinBox()
        self.pos_z.setRange(-1000, 1000)
        self.pos_z.setSingleStep(0.1)
        self.pos_z.valueChanged.connect(lambda: self._update_bbox_property("center", 2))
        position_layout.addRow("Z:", self.pos_z)
        
        position_group.setLayout(position_layout)
        properties_layout.addWidget(position_group)
        
        # サイズ編集
        size_group = QGroupBox("サイズ")
        size_layout = QFormLayout()
        
        self.size_x = QDoubleSpinBox()
        self.size_x.setRange(0.1, 100)
        self.size_x.setSingleStep(0.1)
        self.size_x.valueChanged.connect(lambda: self._update_bbox_property("size", 0))
        size_layout.addRow("幅:", self.size_x)
        
        self.size_y = QDoubleSpinBox()
        self.size_y.setRange(0.1, 100)
        self.size_y.setSingleStep(0.1)
        self.size_y.valueChanged.connect(lambda: self._update_bbox_property("size", 1))
        size_layout.addRow("長さ:", self.size_y)
        
        self.size_z = QDoubleSpinBox()
        self.size_z.setRange(0.1, 100)
        self.size_z.setSingleStep(0.1)
        self.size_z.valueChanged.connect(lambda: self._update_bbox_property("size", 2))
        size_layout.addRow("高さ:", self.size_z)
        
        size_group.setLayout(size_layout)
        properties_layout.addWidget(size_group)
        
        # 回転編集
        rotation_group = QGroupBox("回転")
        rotation_layout = QFormLayout()
        
        self.rot_x = QDoubleSpinBox()
        self.rot_x.setRange(-180, 180)
        self.rot_x.setSingleStep(1)
        self.rot_x.valueChanged.connect(lambda: self._update_bbox_property("rotation", 0))
        rotation_layout.addRow("X軸:", self.rot_x)
        
        self.rot_y = QDoubleSpinBox()
        self.rot_y.setRange(-180, 180)
        self.rot_y.setSingleStep(1)
        self.rot_y.valueChanged.connect(lambda: self._update_bbox_property("rotation", 1))
        rotation_layout.addRow("Y軸:", self.rot_y)
        
        self.rot_z = QDoubleSpinBox()
        self.rot_z.setRange(-180, 180)
        self.rot_z.setSingleStep(1)
        self.rot_z.valueChanged.connect(lambda: self._update_bbox_property("rotation", 2))
        rotation_layout.addRow("Z軸:", self.rot_z)
        
        rotation_group.setLayout(rotation_layout)
        properties_layout.addWidget(rotation_group)
        
        properties_group.setLayout(properties_layout)
        layout.addWidget(properties_group)
        
        # プロパティの編集を初期状態では無効化
        self._set_properties_enabled(False)
        
        return control_panel
    
    def _set_properties_enabled(self, enabled):
        """プロパティ編集の有効/無効を切り替え"""
        self.class_combo.setEnabled(enabled)
        self.pos_x.setEnabled(enabled)
        self.pos_y.setEnabled(enabled)
        self.pos_z.setEnabled(enabled)
        self.size_x.setEnabled(enabled)
        self.size_y.setEnabled(enabled)
        self.size_z.setEnabled(enabled)
        self.rot_x.setEnabled(enabled)
        self.rot_y.setEnabled(enabled)
        self.rot_z.setEnabled(enabled)
    
    def _load_class_labels(self):
        """クラスラベルの読み込み"""
        class_file = os.path.join("class_labels", "classes.json")
        
        if os.path.exists(class_file):
            self.class_manager = ClassManager.load_from_file(class_file)
        else:
            # デフォルトのクラスを作成
            self.class_manager = ClassManager()
            car_class = ClassLabel("car_01", "car", [255, 0, 0])
            pedestrian_class = ClassLabel("pedestrian_01", "pedestrian", [0, 255, 0])
            bicycle_class = ClassLabel("bicycle_01", "bicycle", [0, 0, 255])
            
            self.class_manager.add_class(car_class)
            self.class_manager.add_class(pedestrian_class)
            self.class_manager.add_class(bicycle_class)
    
    def _update_class_combo(self):
        """クラス選択コンボボックスを更新"""
        self.class_combo.clear()
        
        for class_label in self.class_manager.get_all_classes():
            self.class_combo.addItem(class_label.label, class_label.id)
    
    def _update_annotation_list(self):
        """アノテーションリストを更新"""
        self.annotation_list.clear()
        
        for bbox in self.annotation_manager.get_all_annotations():
            item = QListWidgetItem(f"{bbox.class_label} ({bbox.id[:8]}...)")
            item.setData(Qt.UserRole, bbox.id)
            self.annotation_list.addItem(item)
    
    def _update_property_fields(self, bbox: BoundingBox3D):
        """プロパティフィールドを更新"""
        # 値の変更中にシグナルが発火しないようにブロック
        self._block_property_signals(True)
        
        # クラスの設定
        index = self.class_combo.findData(bbox.class_id)
        if index >= 0:
            self.class_combo.setCurrentIndex(index)
        
        # 位置の設定
        self.pos_x.setValue(bbox.center[0])
        self.pos_y.setValue(bbox.center[1])
        self.pos_z.setValue(bbox.center[2])
        
        # サイズの設定
        self.size_x.setValue(bbox.size[0])
        self.size_y.setValue(bbox.size[1])
        self.size_z.setValue(bbox.size[2])
        
        # 回転の設定
        self.rot_x.setValue(bbox.rotation[0])
        self.rot_y.setValue(bbox.rotation[1])
        self.rot_z.setValue(bbox.rotation[2])
        
        # シグナルブロックを解除
        self._block_property_signals(False)
    
    def _block_property_signals(self, block):
        """プロパティフィールドのシグナルをブロック/アンブロック"""
        self.class_combo.blockSignals(block)
        self.pos_x.blockSignals(block)
        self.pos_y.blockSignals(block)
        self.pos_z.blockSignals(block)
        self.size_x.blockSignals(block)
        self.size_y.blockSignals(block)
        self.size_z.blockSignals(block)
        self.rot_x.blockSignals(block)
        self.rot_y.blockSignals(block)
        self.rot_z.blockSignals(block)
    
    def _open_point_cloud(self):
        """点群ファイルを開く"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "点群ファイルを開く", "./data",
            "点群ファイル (*.pcd *.ply *.xyz *.bin);;すべてのファイル (*.*)"
        )
        
        if not file_path:
            return
        
        # 点群の読み込み
        pcd, xyz = load_point_cloud(file_path)
        if pcd is None:
            QMessageBox.critical(self, "エラー", f"点群ファイル '{file_path}' の読み込みに失敗しました。")
            return
        
        # ビューアに点群をセット
        if not self.point_cloud_viewer.load_point_cloud(pcd, xyz):
            QMessageBox.critical(self, "エラー", "点群の表示に失敗しました。")
            return
        
        # 現在のファイルパスを保存
        self.current_file_path = file_path
        file_name = os.path.basename(file_path)
        self.setWindowTitle(f"3Dアノテーションツール - {file_name}")
        
        # 状態を更新
        self.point_cloud = pcd
        self.point_cloud_xyz = xyz
        
        # 対応するアノテーションファイルをチェック
        annotation_file = self._get_annotation_file_path(file_path)
        if os.path.exists(annotation_file):
            # アノテーションファイルが存在する場合は読み込む
            self.annotation_manager = AnnotationManager.load_from_file(annotation_file)
            
            # ビューアにアノテーションを表示
            self._display_all_annotations()
            
            # リストを更新
            self._update_annotation_list()
        else:
            # 新しいアノテーションマネージャを作成
            self.annotation_manager = AnnotationManager()
            
            # ビューアのアノテーションをクリア
            self.point_cloud_viewer.clear_all_bounding_boxes()
            
            # リストをクリア
            self.annotation_list.clear()
        
        self.statusBar.showMessage(f"点群ファイル '{file_name}' を読み込みました")
    
    def _get_annotation_file_path(self, point_cloud_file):
        """点群ファイルに対応するアノテーションファイルのパスを取得"""
        dir_path = os.path.dirname(point_cloud_file)
        file_name = os.path.splitext(os.path.basename(point_cloud_file))[0]
        return os.path.join(dir_path, f"{file_name}_annotation.json")
    
    def _save_annotation(self):
        """アノテーションを保存"""
        if self.current_file_path is None:
            QMessageBox.warning(self, "警告", "点群ファイルが読み込まれていません。")
            return
        
        annotation_file = self._get_annotation_file_path(self.current_file_path)
        
        if self.annotation_manager.save_to_file(annotation_file):
            self.statusBar.showMessage(f"アノテーションを '{annotation_file}' に保存しました")
        else:
            QMessageBox.critical(self, "エラー", f"アノテーションの保存に失敗しました: {annotation_file}")
    
    def _display_all_annotations(self):
        """全てのアノテーションをビューアに表示"""
        # 一度すべてクリア
        self.point_cloud_viewer.clear_all_bounding_boxes()
        
        # すべてのアノテーションを表示
        for bbox in self.annotation_manager.get_all_annotations():
            self.point_cloud_viewer.add_bounding_box(bbox)
    
    def _add_new_box(self):
        """新しいバウンディングボックスを追加"""
        if self.point_cloud is None:
            QMessageBox.warning(self, "警告", "点群が読み込まれていません。")
            return
        
        # デフォルトのクラス情報を取得
        default_class = self.class_manager.get_all_classes()[0]
        
        # デフォルトの中心位置を計算（点群の中心）
        point_cloud_center = np.mean(self.point_cloud_xyz, axis=0).tolist()
        
        # 新しいバウンディングボックスを作成
        bbox = BoundingBox3D(
            center=point_cloud_center,
            size=[2.0, 4.0, 1.5],  # デフォルトサイズ
            rotation=[0.0, 0.0, 0.0],
            class_id=default_class.id,
            class_label=default_class.label,
            class_color=default_class.color
        )
        
        # アノテーションマネージャに追加
        bbox_id = self.annotation_manager.add_annotation(bbox)
        
        # ビューアに表示
        self.point_cloud_viewer.add_bounding_box(bbox)
        
        # リストを更新
        self._update_annotation_list()
        
        # 作成したボックスを選択
        self.point_cloud_viewer.select_bounding_box(bbox_id)
        
        # リストでも選択
        for i in range(self.annotation_list.count()):
            item = self.annotation_list.item(i)
            if item.data(Qt.UserRole) == bbox_id:
                self.annotation_list.setCurrentItem(item)
                break
        
        self.statusBar.showMessage(f"新しいバウンディングボックスを作成しました (ID: {bbox_id[:8]}...)")
    
    def _delete_selected_box(self):
        """選択されたバウンディングボックスを削除"""
        selected_id = None
        
        # リストから選択されたアイテムがあればそのIDを取得
        selected_items = self.annotation_list.selectedItems()
        if selected_items:
            selected_id = selected_items[0].data(Qt.UserRole)
        # リストで選択されていない場合はビューアの選択を使用
        elif self.point_cloud_viewer.selected_box_id:
            selected_id = self.point_cloud_viewer.selected_box_id
        
        if not selected_id:
            QMessageBox.warning(self, "警告", "削除するバウンディングボックスが選択されていません。")
            return
        
        # 削除の確認
        reply = QMessageBox.question(
            self, "確認", f"選択されたバウンディングボックス (ID: {selected_id[:8]}...) を削除しますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # マネージャから削除
        if self.annotation_manager.remove_annotation(selected_id):
            # ビューアからも削除
            self.point_cloud_viewer.remove_bounding_box(selected_id)
            
            # リストを更新
            self._update_annotation_list()
            
            # プロパティ編集を無効化
            self._set_properties_enabled(False)
            
            self.statusBar.showMessage(f"バウンディングボックス (ID: {selected_id[:8]}...) を削除しました")
        else:
            QMessageBox.critical(self, "エラー", f"バウンディングボックスの削除に失敗しました (ID: {selected_id[:8]}...)")
    
    def _on_bbox_selected(self, bbox_id):
        """バウンディングボックスが選択されたときの処理"""
        # マネージャからバウンディングボックスを取得
        bbox = self.annotation_manager.get_annotation(bbox_id)
        if not bbox:
            return
        
        # プロパティ編集を有効化
        self._set_properties_enabled(True)
        
        # プロパティフィールドを更新
        self._update_property_fields(bbox)
        
        # リストでも選択
        for i in range(self.annotation_list.count()):
            item = self.annotation_list.item(i)
            if item.data(Qt.UserRole) == bbox_id:
                self.annotation_list.setCurrentItem(item)
                break
        
        self.statusBar.showMessage(f"バウンディングボックス (ID: {bbox_id[:8]}...) を選択しました")
    
    def _on_bbox_created(self, bbox):
        """バウンディングボックスが作成されたときの処理"""
        # マネージャに追加
        bbox_id = self.annotation_manager.add_annotation(bbox)
        
        # リストを更新
        self._update_annotation_list()
        
        # 作成したボックスを選択
        self.point_cloud_viewer.select_bounding_box(bbox_id)
        
        self.statusBar.showMessage(f"新しいバウンディングボックスを作成しました (ID: {bbox_id[:8]}...)")
    
    def _on_annotation_item_clicked(self, item):
        """アノテーションリストのアイテムがクリックされたときの処理"""
        bbox_id = item.data(Qt.UserRole)
        self.point_cloud_viewer.select_bounding_box(bbox_id)
    
    def _on_class_changed(self, index):
        """クラス選択が変更されたときの処理"""
        if index < 0 or self.point_cloud_viewer.selected_box_id is None:
            return
        
        # 選択されたクラスIDを取得
        class_id = self.class_combo.itemData(index)
        class_label = self.class_combo.itemText(index)
        
        # クラスの色を取得
        class_obj = self.class_manager.get_class(class_id)
        if not class_obj:
            return
        
        # 更新データを作成
        update_data = {
            "class_id": class_id,
            "class_label": class_label,
            "class_color": class_obj.color
        }
        
        # 選択されたバウンディングボックスを更新
        bbox_id = self.point_cloud_viewer.selected_box_id
        if self.annotation_manager.update_annotation(bbox_id, update_data):
            # ビューアも更新
            bbox = self.annotation_manager.get_annotation(bbox_id)
            self.point_cloud_viewer.update_bounding_box(bbox)
            
            # リストを更新
            self._update_annotation_list()
            
            self.statusBar.showMessage(f"バウンディングボックスのクラスを '{class_label}' に変更しました")
    
    def _update_bbox_property(self, property_name, index):
        """バウンディングボックスのプロパティを更新"""
        if self.point_cloud_viewer.selected_box_id is None:
            return
        
        bbox_id = self.point_cloud_viewer.selected_box_id
        bbox = self.annotation_manager.get_annotation(bbox_id)
        if not bbox:
            return
        
        # 現在の値を取得
        values = getattr(bbox, property_name).copy()
        
        # 新しい値を設定
        if property_name == "center":
            values[index] = self.pos_x.value() if index == 0 else (
                self.pos_y.value() if index == 1 else self.pos_z.value()
            )
        elif property_name == "size":
            values[index] = self.size_x.value() if index == 0 else (
                self.size_y.value() if index == 1 else self.size_z.value()
            )
        elif property_name == "rotation":
            values[index] = self.rot_x.value() if index == 0 else (
                self.rot_y.value() if index == 1 else self.rot_z.value()
            )
        
        # 更新データを作成
        update_data = {property_name: values}
        
        # バウンディングボックスを更新
        if self.annotation_manager.update_annotation(bbox_id, update_data):
            # ビューアも更新
            bbox = self.annotation_manager.get_annotation(bbox_id)
            self.point_cloud_viewer.update_bounding_box(bbox)
            
            property_labels = {
                "center": "位置",
                "size": "サイズ",
                "rotation": "回転"
            }
            self.statusBar.showMessage(f"バウンディングボックスの{property_labels[property_name]}を更新しました")
    
    def _undo(self):
        """操作を元に戻す"""
        if self.annotation_manager.undo():
            # ビューアの表示を更新
            self._display_all_annotations()
            
            # リストを更新
            self._update_annotation_list()
            
            self.statusBar.showMessage("操作を元に戻しました")
        else:
            self.statusBar.showMessage("これ以上元に戻せる操作はありません")
    
    def _redo(self):
        """操作をやり直す"""
        if self.annotation_manager.redo():
            # ビューアの表示を更新
            self._display_all_annotations()
            
            # リストを更新
            self._update_annotation_list()
            
            self.statusBar.showMessage("操作をやり直しました")
        else:
            self.statusBar.showMessage("これ以上やり直せる操作はありません")
    
    def closeEvent(self, event):
        """ウィンドウが閉じられるときの処理"""
        # ビューアを閉じる
        self.point_cloud_viewer.close_viewer()
        event.accept() 