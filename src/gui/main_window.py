import os
import sys
import json
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QComboBox, QListWidget,
    QListWidgetItem, QMessageBox, QGroupBox, QFormLayout, QDoubleSpinBox,
    QStatusBar, QToolBar, QCheckBox, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt, Slot, QDir
from PySide6.QtGui import QIcon, QKeySequence, QAction

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import BoundingBox3D, ClassLabel, AnnotationManager, ClassManager
from src.utils import load_point_cloud
from src.coordinate_transform import enable_transform, is_transform_enabled, get_available_systems, get_system_info
from src.gui.point_cloud_viewer import PointCloudViewer
from src.gui.fixed_view_viewer import FixedViewViewer, ViewType
from src.frame_manager import FrameManager
from src.tracking_manager import TrackingManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # ウィンドウ設定
        self.setWindowTitle("3D Annotation Tool")
        self.setMinimumSize(1200, 800)
        
        # データ管理
        self.current_file_path = None
        self.annotation_manager = AnnotationManager()
        self.class_manager = ClassManager()
        self.point_cloud = None
        self.point_cloud_xyz = None
        
        # フレーム管理とトラッキング管理
        self.frame_manager = FrameManager()
        self.tracking_manager = TrackingManager()
        
        # クラスラベルの読み込み
        self._load_class_labels()
        
        # UIの初期化
        self._init_ui()
        
        # キーボードショートカットの設定
        self._setup_shortcuts()
    
    def _init_ui(self):
        """UIコンポーネントの初期化"""
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QVBoxLayout(central_widget)
        
        # ツールバー
        self._create_toolbar()
        
        # メインコンテンツのスプリッター（横方向の3分割）
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # 左側のコントロールパネル
        control_panel = self._create_control_panel()
        main_splitter.addWidget(control_panel)
        
        # 中央の点群ビューアー
        self.point_cloud_viewer = PointCloudViewer()
        self.point_cloud_viewer.box_selected.connect(self._on_bbox_selected)
        self.point_cloud_viewer.box_created.connect(self._on_bbox_created)
        main_splitter.addWidget(self.point_cloud_viewer)
        
        # 右側のマルチビューパネル
        multi_view_panel = self._create_multi_view_panel()
        main_splitter.addWidget(multi_view_panel)
        
        # スプリッターの初期サイズ比率設定（左:中央:右 = 2:5:3）
        main_splitter.setSizes([200, 500, 300])
        
        # タイムラインコントロールパネル
        timeline_panel = self._create_timeline_panel()
        main_layout.addWidget(timeline_panel)
        
        # ステータスバー
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def _create_toolbar(self):
        """ツールバーの作成"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # ファイル操作
        open_action = QAction("Open Point Cloud", self)
        open_action.triggered.connect(self._open_point_cloud)
        toolbar.addAction(open_action)
        
        open_sequence_action = QAction("Open Sequence", self)
        open_sequence_action.triggered.connect(self._open_sequence)
        toolbar.addAction(open_sequence_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self._save_annotation)
        toolbar.addAction(save_action)
        
        # 編集操作
        toolbar.addSeparator()
        
        undo_action = QAction("Undo", self)
        undo_action.triggered.connect(self._undo)
        undo_action.setShortcut(QKeySequence.Undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.triggered.connect(self._redo)
        redo_action.setShortcut(QKeySequence.Redo)
        toolbar.addAction(redo_action)
        
        # アノテーション操作
        toolbar.addSeparator()
        
        add_box_action = QAction("Add Box", self)
        add_box_action.triggered.connect(self._add_new_box)
        toolbar.addAction(add_box_action)
        
        delete_box_action = QAction("Delete", self)
        delete_box_action.triggered.connect(self._delete_selected_box)
        toolbar.addAction(delete_box_action)
        
        # 座標変換操作
        toolbar.addSeparator()
        
        # 座標変換の有効/無効を切り替えるチェックボックス
        self.transform_checkbox = QCheckBox("Coordinate Transform", self)
        self.transform_checkbox.setChecked(is_transform_enabled())
        self.transform_checkbox.stateChanged.connect(self._toggle_coordinate_transform)
        toolbar.addWidget(self.transform_checkbox)
    
    def _create_timeline_panel(self):
        """タイムラインコントロールパネルの作成"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        
        # 前のフレームボタン
        self.prev_frame_button = QPushButton("Previous Frame")
        self.prev_frame_button.clicked.connect(self._prev_frame)
        self.prev_frame_button.setEnabled(False)
        layout.addWidget(self.prev_frame_button)
        
        # 現在のフレーム表示
        self.frame_label = QLabel("No frame")
        layout.addWidget(self.frame_label)
        
        # 次のフレームボタン
        self.next_frame_button = QPushButton("Next Frame")
        self.next_frame_button.clicked.connect(self._next_frame)
        self.next_frame_button.setEnabled(False)
        layout.addWidget(self.next_frame_button)
        
        # フレーム選択ボタン
        self.goto_frame_button = QPushButton("Go to Frame...")
        self.goto_frame_button.clicked.connect(self._goto_frame)
        self.goto_frame_button.setEnabled(False)
        layout.addWidget(self.goto_frame_button)
        
        # アノテーション伝播ボタン
        self.propagate_button = QPushButton("Propagate to Next Frame")
        self.propagate_button.clicked.connect(self._propagate_to_next_frame)
        self.propagate_button.setEnabled(False)
        layout.addWidget(self.propagate_button)
        
        return panel
    
    def _setup_shortcuts(self):
        """キーボードショートカットの設定"""
        # 前のフレームへ移動（左矢印キー）
        prev_frame_shortcut = QAction("Previous Frame", self)
        prev_frame_shortcut.setShortcut(Qt.Key_Left)
        prev_frame_shortcut.triggered.connect(self._prev_frame)
        self.addAction(prev_frame_shortcut)
        
        # 次のフレームへ移動（右矢印キー）
        next_frame_shortcut = QAction("Next Frame", self)
        next_frame_shortcut.setShortcut(Qt.Key_Right)
        next_frame_shortcut.triggered.connect(self._next_frame)
        self.addAction(next_frame_shortcut)
        
        # 特定のフレームへ移動（G）
        goto_frame_shortcut = QAction("Go to Frame", self)
        goto_frame_shortcut.setShortcut(Qt.Key_G)
        goto_frame_shortcut.triggered.connect(self._goto_frame)
        self.addAction(goto_frame_shortcut)
        
        # アノテーション伝播（P）
        propagate_shortcut = QAction("Propagate Annotations", self)
        propagate_shortcut.setShortcut(Qt.Key_P)
        propagate_shortcut.triggered.connect(self._propagate_to_next_frame)
        self.addAction(propagate_shortcut)
    
    def _open_sequence(self):
        """シーケンスを開く"""
        # 前回開いたディレクトリを記憶
        last_dir = getattr(self, 'last_open_dir', None)
        if not last_dir:
            last_dir = QDir.homePath()
        
        # ディレクトリ選択ダイアログ
        directory = QFileDialog.getExistingDirectory(
            self,
            "Open Sequence Directory",
            last_dir,
            QFileDialog.ShowDirsOnly
        )
        
        if not directory:
            return
        
        # ディレクトリを記憶
        self.last_open_dir = directory
        
        # フレームシーケンスを読み込み
        if not self.frame_manager.load_sequence(directory):
            # フレームがない場合は新規作成するか確認
            reply = QMessageBox.question(
                self,
                "No Frames Found",
                "No frames found in the selected directory. Would you like to create a new frame structure?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # フレーム数を尋ねる
                num_frames, ok = QInputDialog.getInt(
                    self,
                    "Create Frame Structure",
                    "Number of frames to create:",
                    10, 1, 1000, 1
                )
                
                if ok:
                    self.frame_manager.create_frame_structure(directory, num_frames)
                else:
                    return
            else:
                return
        
        # トラッキングマネージャの設定
        self.tracking_manager.set_project_root(directory)
        self.tracking_manager.load_track_info()
        
        # 最初のフレームを読み込み
        self._load_current_frame()
        
        # UIの有効化
        self._update_frame_controls()
    
    def _load_current_frame(self):
        """現在のフレームを読み込み"""
        # 現在のフレームの点群ファイルを取得
        point_cloud_file = self.frame_manager.get_current_frame()
        if not point_cloud_file:
            QMessageBox.warning(self, "Warning", "No point cloud file for current frame.")
            return False
        
        # 点群データを読み込み
        self.point_cloud_xyz, self.point_cloud = load_point_cloud(point_cloud_file)
        
        if self.point_cloud_xyz is None:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load point cloud file: {point_cloud_file}"
            )
            return False
        
        # ビューアに点群をセット
        if not self.point_cloud_viewer.load_point_cloud(self.point_cloud, self.point_cloud_xyz):
            QMessageBox.critical(self, "Error", "Failed to display point cloud.")
            return False
        
        # 現在のファイルパスを保存
        self.current_file_path = point_cloud_file
        file_name = os.path.basename(point_cloud_file)
        
        # フレームIDを取得
        current_frame_id = self.frame_manager.get_current_frame_id()
        self.setWindowTitle(f"3D Annotation Tool - Frame {current_frame_id} - {file_name}")
        
        # フレームラベルを更新
        frame_count = self.frame_manager.get_frame_count()
        self.frame_label.setText(f"Frame {current_frame_id} / {frame_count}")
        
        # 対応するアノテーションファイルをチェック
        annotation_file = self.frame_manager.get_annotation_file_path()
        
        if os.path.exists(annotation_file):
            # アノテーションファイルが存在する場合は読み込む
            self.annotation_manager = AnnotationManager.load_from_file(annotation_file)
            
            # ビューアにアノテーションを表示
            self._display_all_annotations()
            
            # リストを更新
            self._update_annotation_list()
        else:
            # 新しいアノテーションマネージャを作成
            self.annotation_manager = AnnotationManager(frame_id=current_frame_id)
            
            # ビューアのアノテーションをクリア
            self.point_cloud_viewer.clear_all_bounding_boxes()
            
            # リストをクリア
            self.annotation_list.clear()
        
        # マルチビューも更新
        self._update_multi_views()
        
        self.statusBar.showMessage(f"Loaded frame {current_frame_id} - '{file_name}'")
        return True
    
    def _update_frame_controls(self):
        """フレームコントロールの有効/無効を更新"""
        has_frames = self.frame_manager.get_frame_count() > 0
        
        self.prev_frame_button.setEnabled(has_frames)
        self.next_frame_button.setEnabled(has_frames)
        self.goto_frame_button.setEnabled(has_frames)
        self.propagate_button.setEnabled(has_frames)
    
    def _prev_frame(self):
        """前のフレームに移動"""
        # 現在のアノテーションを保存
        self._save_current_annotation()
        
        # 前のフレームに移動
        if self.frame_manager.prev_frame():
            self._load_current_frame()
    
    def _next_frame(self):
        """次のフレームに移動"""
        # 現在のアノテーションを保存
        self._save_current_annotation()
        
        # 次のフレームに移動
        if self.frame_manager.next_frame():
            self._load_current_frame()
    
    def _goto_frame(self):
        """特定のフレームに移動"""
        # 利用可能なフレームIDを取得
        frame_ids = self.frame_manager.get_all_frame_ids()
        if not frame_ids:
            return
        
        # 現在のフレームIDを取得
        current_frame_id = self.frame_manager.get_current_frame_id() or frame_ids[0]
        
        # フレームID選択ダイアログ
        frame_id, ok = QInputDialog.getItem(
            self,
            "Go to Frame",
            "Select frame:",
            frame_ids,
            frame_ids.index(current_frame_id) if current_frame_id in frame_ids else 0,
            False
        )
        
        if ok and frame_id:
            # 現在のアノテーションを保存
            self._save_current_annotation()
            
            # 選択したフレームに移動
            if self.frame_manager.goto_frame(frame_id):
                self._load_current_frame()
    
    def _save_current_annotation(self):
        """現在のフレームのアノテーションを保存"""
        if self.current_file_path:
            # アノテーションファイルのパスを取得
            annotation_file = self.frame_manager.get_annotation_file_path()
            
            # フレームIDを設定
            self.annotation_manager.set_frame_id(self.frame_manager.get_current_frame_id())
            
            # 保存
            if self.annotation_manager.save_to_file(annotation_file):
                self.statusBar.showMessage(f"Saved annotations to '{annotation_file}'")
            else:
                QMessageBox.warning(self, "Warning", f"Failed to save annotations: {annotation_file}")
    
    def _propagate_to_next_frame(self):
        """現在のフレームのアノテーションを次のフレームに伝播"""
        # 現在のフレームIDを取得
        current_frame_id = self.frame_manager.get_current_frame_id()
        if not current_frame_id:
            return
        
        # 利用可能なフレームIDを取得
        frame_ids = self.frame_manager.get_all_frame_ids()
        if not frame_ids or len(frame_ids) <= 1:
            QMessageBox.warning(self, "Warning", "No frames to propagate to.")
            return
        
        # 現在のインデックスを取得
        try:
            current_index = frame_ids.index(current_frame_id)
        except ValueError:
            QMessageBox.warning(self, "Warning", "Current frame not found in sequence.")
            return
        
        # 次のフレームのインデックスを計算
        next_index = (current_index + 1) % len(frame_ids)
        next_frame_id = frame_ids[next_index]
        
        # 伝播を実行
        if self.tracking_manager.propagate_annotations(
            self.annotation_manager, current_frame_id, next_frame_id
        ):
            self.statusBar.showMessage(f"Propagated annotations from frame {current_frame_id} to {next_frame_id}")
            
            # 自動的に次のフレームに移動するか確認
            reply = QMessageBox.question(
                self,
                "Propagation Complete",
                f"Annotations propagated to frame {next_frame_id}.\n\nNote: Boxes with the same track ID were updated rather than duplicated. Go to that frame now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # 現在のアノテーションを保存
                self._save_current_annotation()
                
                # 次のフレームに移動
                if self.frame_manager.goto_frame(next_frame_id):
                    self._load_current_frame()
        else:
            QMessageBox.warning(
                self,
                "Propagation Failed",
                f"Failed to propagate annotations to frame {next_frame_id}."
            )
    
    def _create_control_panel(self):
        """コントロールパネルの作成"""
        control_panel = QWidget()
        layout = QVBoxLayout(control_panel)
        
        # 1. アノテーションリスト
        annotation_group = QGroupBox("Annotation List")
        annotation_layout = QVBoxLayout()
        
        self.annotation_list = QListWidget()
        self.annotation_list.itemClicked.connect(self._on_annotation_item_clicked)
        annotation_layout.addWidget(self.annotation_list)
        
        annotation_buttons_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_new_box)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._delete_selected_box)
        annotation_buttons_layout.addWidget(add_button)
        annotation_buttons_layout.addWidget(delete_button)
        annotation_layout.addLayout(annotation_buttons_layout)
        
        annotation_group.setLayout(annotation_layout)
        layout.addWidget(annotation_group)
        
        # 2. 選択されたボックスのプロパティ
        properties_group = QGroupBox("Properties")
        properties_layout = QFormLayout()
        
        # クラス選択
        self.class_combo = QComboBox()
        self._update_class_combo()
        properties_layout.addRow("Class:", self.class_combo)
        self.class_combo.currentIndexChanged.connect(self._on_class_changed)
        
        # 寸法と位置の編集
        position_group = QGroupBox("Position")
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
        size_group = QGroupBox("Size")
        size_layout = QFormLayout()
        
        self.size_x = QDoubleSpinBox()
        self.size_x.setRange(0.1, 100)
        self.size_x.setSingleStep(0.1)
        self.size_x.valueChanged.connect(lambda: self._update_bbox_property("size", 0))
        size_layout.addRow("Width:", self.size_x)
        
        self.size_y = QDoubleSpinBox()
        self.size_y.setRange(0.1, 100)
        self.size_y.setSingleStep(0.1)
        self.size_y.valueChanged.connect(lambda: self._update_bbox_property("size", 1))
        size_layout.addRow("Length:", self.size_y)
        
        self.size_z = QDoubleSpinBox()
        self.size_z.setRange(0.1, 100)
        self.size_z.setSingleStep(0.1)
        self.size_z.valueChanged.connect(lambda: self._update_bbox_property("size", 2))
        size_layout.addRow("Height:", self.size_z)
        
        size_group.setLayout(size_layout)
        properties_layout.addWidget(size_group)
        
        # 回転編集
        rotation_group = QGroupBox("Rotation")
        rotation_layout = QFormLayout()
        
        self.rot_x = QDoubleSpinBox()
        self.rot_x.setRange(-180, 180)
        self.rot_x.setSingleStep(1)
        self.rot_x.valueChanged.connect(lambda: self._update_bbox_property("rotation", 0))
        rotation_layout.addRow("X-axis:", self.rot_x)
        
        self.rot_y = QDoubleSpinBox()
        self.rot_y.setRange(-180, 180)
        self.rot_y.setSingleStep(1)
        self.rot_y.valueChanged.connect(lambda: self._update_bbox_property("rotation", 1))
        rotation_layout.addRow("Y-axis:", self.rot_y)
        
        self.rot_z = QDoubleSpinBox()
        self.rot_z.setRange(-180, 180)
        self.rot_z.setSingleStep(1)
        self.rot_z.valueChanged.connect(lambda: self._update_bbox_property("rotation", 2))
        rotation_layout.addRow("Z-axis:", self.rot_z)
        
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
        # 前回開いたディレクトリを記憶
        last_dir = getattr(self, 'last_open_dir', None)
        if not last_dir:
            last_dir = QDir.homePath()
        
        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Point Cloud File",
            last_dir,
            "Point Cloud Files (*.pcd *.npy)"
        )
        
        if not file_path:
            return
        
        # ディレクトリを記憶
        self.last_open_dir = os.path.dirname(file_path)
        
        # 座標変換の状態を表示
        transform_status = "enabled" if is_transform_enabled() else "disabled"
        self.statusBar.showMessage(f"Loading point cloud file... Coordinate transform: {transform_status}")
        
        # 点群データを読み込み
        self.point_cloud_xyz, self.point_cloud = load_point_cloud(file_path)
        
        if self.point_cloud_xyz is None:
            QMessageBox.critical(
                self,
                "Load Error",
                f"Failed to load point cloud file: {file_path}"
            )
            return
        
        # ビューアに点群をセット
        if not self.point_cloud_viewer.load_point_cloud(self.point_cloud, self.point_cloud_xyz):
            QMessageBox.critical(self, "Error", "Failed to display point cloud.")
            return
        
        # 現在のファイルパスを保存
        self.current_file_path = file_path
        file_name = os.path.basename(file_path)
        self.setWindowTitle(f"3D Annotation Tool - {file_name}")
        
        # 状態を更新
        self.point_cloud = self.point_cloud
        self.point_cloud_xyz = self.point_cloud_xyz
        
        # マルチビューも更新
        self._update_multi_views()
        
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
        
        self.statusBar.showMessage(f"Loaded point cloud file '{file_name}'")
    
    def _get_annotation_file_path(self, point_cloud_file):
        """点群ファイルに対応するアノテーションファイルのパスを取得"""
        dir_path = os.path.dirname(point_cloud_file)
        file_name = os.path.splitext(os.path.basename(point_cloud_file))[0]
        return os.path.join(dir_path, f"{file_name}_annotation.json")
    
    def _save_annotation(self):
        """アノテーションを保存"""
        if self.current_file_path is None:
            QMessageBox.warning(self, "Warning", "No point cloud file is loaded.")
            return
        
        annotation_file = self._get_annotation_file_path(self.current_file_path)
        
        if self.annotation_manager.save_to_file(annotation_file):
            self.statusBar.showMessage(f"Saved annotations to '{annotation_file}'")
        else:
            QMessageBox.critical(self, "Error", f"Failed to save annotations: {annotation_file}")
    
    def _display_all_annotations(self):
        """全てのアノテーションをビューアに表示"""
        # 一度すべてクリア
        self.point_cloud_viewer.clear_all_bounding_boxes()
        
        # すべてのアノテーションを表示
        for bbox in self.annotation_manager.get_all_annotations():
            self.point_cloud_viewer.add_bounding_box(bbox)
        
        # マルチビューも更新
        self._update_multi_views()
    
    def _add_new_box(self):
        """新しいバウンディングボックスを追加"""
        if self.point_cloud is None:
            QMessageBox.warning(self, "Warning", "No point cloud is loaded.")
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
        
        self.statusBar.showMessage(f"Created new bounding box (ID: {bbox_id[:8]}...)")
    
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
            QMessageBox.warning(self, "Warning", "No bounding box is selected to delete.")
            return
        
        # 削除の確認
        reply = QMessageBox.question(
            self, "Confirm", f"Delete selected bounding box (ID: {selected_id[:8]}...)?",
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
            
            # マルチビューも更新
            self._update_multi_views()
            
            self.statusBar.showMessage(f"Deleted bounding box (ID: {selected_id[:8]}...)")
        else:
            QMessageBox.critical(self, "Error", f"Failed to delete bounding box (ID: {selected_id[:8]}...)")
    
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
        
        # マルチビューを更新
        self._update_multi_views()
        
        self.statusBar.showMessage(f"Selected bounding box (ID: {bbox_id[:8]}...)")
    
    def _on_bbox_created(self, bbox):
        """バウンディングボックスが作成されたときの処理"""
        # マネージャに追加
        bbox_id = self.annotation_manager.add_annotation(bbox)
        
        # リストを更新
        self._update_annotation_list()
        
        # 作成したボックスを選択
        self.point_cloud_viewer.select_bounding_box(bbox_id)
        
        # マルチビューを更新
        self._update_multi_views()
        
        self.statusBar.showMessage(f"Created new bounding box (ID: {bbox_id[:8]}...)")
    
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
            
            # マルチビューも更新
            self._update_multi_views()
            
            # リストを更新
            self._update_annotation_list()
            
            self.statusBar.showMessage(f"Changed bounding box class to '{class_label}'")
    
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
            
            # マルチビューも更新
            self._update_multi_views()
            
            property_labels = {
                "center": "position",
                "size": "size",
                "rotation": "rotation"
            }
            self.statusBar.showMessage(f"Updated bounding box {property_labels[property_name]}")
    
    def _undo(self):
        """操作を元に戻す"""
        if self.annotation_manager.undo():
            # ビューアの表示を更新
            self._display_all_annotations()
            
            # リストを更新
            self._update_annotation_list()
            
            # マルチビューも更新
            self._update_multi_views()
            
            self.statusBar.showMessage("Undid last operation")
        else:
            self.statusBar.showMessage("No more operations to undo")
    
    def _redo(self):
        """操作をやり直す"""
        if self.annotation_manager.redo():
            # ビューアの表示を更新
            self._display_all_annotations()
            
            # リストを更新
            self._update_annotation_list()
            
            # マルチビューも更新
            self._update_multi_views()
            
            self.statusBar.showMessage("操作をやり直しました")
        else:
            self.statusBar.showMessage("これ以上やり直せる操作はありません")
    
    def closeEvent(self, event):
        """ウィンドウが閉じられるときの処理"""
        # ビューアを閉じる
        self.point_cloud_viewer.close_viewer()
        
        # マルチビューも閉じる
        self.top_view.close_viewer()
        self.front_view.close_viewer()
        self.side_view.close_viewer()
        
        event.accept()

    def _create_multi_view_panel(self):
        """マルチビューパネル（上面・正面・側面ビュー）の作成"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 垂直方向のスプリッター
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # 上面ビュー
        self.top_view = FixedViewViewer(ViewType.TOP)
        splitter.addWidget(self.top_view)
        
        # 正面ビュー
        self.front_view = FixedViewViewer(ViewType.FRONT)
        splitter.addWidget(self.front_view)
        
        # 側面ビュー
        self.side_view = FixedViewViewer(ViewType.SIDE)
        splitter.addWidget(self.side_view)
        
        # 各ビューの高さを均等に設定
        splitter.setSizes([1, 1, 1])
        
        return panel

    def _update_multi_views(self):
        """マルチビューを更新する"""
        # メインビューアからデータを同期
        self.top_view.sync_from_main_viewer(self.point_cloud_viewer)
        self.front_view.sync_from_main_viewer(self.point_cloud_viewer)
        self.side_view.sync_from_main_viewer(self.point_cloud_viewer)

    def _toggle_coordinate_transform(self, state):
        """座標変換の有効/無効を切り替える"""
        enabled = state == Qt.Checked
        enable_transform(enabled)
        
        # 変更を表示
        status = "有効" if enabled else "無効"
        self.statusBar.showMessage(f"座標変換を{status}にしました。次回の点群読み込み時に適用されます。")
        
        # チェックボックスの状態を更新
        self.transform_checkbox.setChecked(is_transform_enabled()) 