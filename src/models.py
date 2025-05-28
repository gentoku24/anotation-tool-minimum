import json
import os
import numpy as np
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

class BoundingBox3D:
    """3Dバウンディングボックスを表すクラス"""
    
    def __init__(self, center: List[float], size: List[float], rotation: List[float], 
                 id: str = None, class_id: str = None, class_label: str = None, 
                 class_color: List[int] = None, track_id: str = None):
        # タイムスタンプと一意なUUIDを組み合わせてより確実にユニークなIDを生成
        self.id = id or f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{str(uuid.uuid4())[:8]}"
        self.class_id = class_id
        self.class_label = class_label
        self.class_color = class_color or [255, 255, 255]  # デフォルトは白
        self.center = center  # [x, y, z]
        self.size = size  # [width, length, height]
        self.rotation = rotation  # [rx, ry, rz] - 各軸周りの回転角度（度数法）
        self.track_id = track_id or self.id  # デフォルトはボックスIDと同じ
    
    def to_dict(self) -> Dict[str, Any]:
        """オブジェクトを辞書形式に変換"""
        return {
            "id": self.id,
            "class_id": self.class_id,
            "class_label": self.class_label,
            "class_color": self.class_color,
            "center": self.center,
            "size": self.size,
            "rotation": self.rotation,
            "track_id": self.track_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BoundingBox3D':
        """辞書からBoundingBox3Dオブジェクトを作成"""
        return cls(
            id=data.get("id"),
            class_id=data.get("class_id"),
            class_label=data.get("class_label"),
            class_color=data.get("class_color"),
            center=data.get("center"),
            size=data.get("size"),
            rotation=data.get("rotation"),
            track_id=data.get("track_id")
        )

class ClassLabel:
    """アノテーションのクラスラベルを表すクラス"""
    
    def __init__(self, id: str, label: str, color: List[int]):
        self.id = id
        self.label = label
        self.color = color
    
    def to_dict(self) -> Dict[str, Any]:
        """オブジェクトを辞書形式に変換"""
        return {
            "id": self.id,
            "label": self.label,
            "color": self.color
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassLabel':
        """辞書からClassLabelオブジェクトを作成"""
        return cls(
            id=data.get("id"),
            label=data.get("label"),
            color=data.get("color")
        )

class AnnotationManager:
    """アノテーションの管理を行うクラス"""
    
    def __init__(self, frame_id: str = "00000"):
        self.frame_id = frame_id
        self.annotations: List[BoundingBox3D] = []
        self.history: List[Dict[str, Any]] = []
        self.redo_stack: List[Dict[str, Any]] = []
    
    def add_annotation(self, annotation: BoundingBox3D) -> str:
        """アノテーションを追加"""
        self.annotations.append(annotation)
        # 操作履歴に追加
        self.history.append({
            "action": "add",
            "annotation_id": annotation.id,
            "data": annotation.to_dict()
        })
        self.redo_stack = []  # Redoスタックをクリア
        return annotation.id
    
    def remove_annotation(self, annotation_id: str) -> bool:
        """アノテーションを削除"""
        for i, annotation in enumerate(self.annotations):
            if annotation.id == annotation_id:
                removed_annotation = self.annotations.pop(i)
                # 操作履歴に追加
                self.history.append({
                    "action": "remove",
                    "annotation_id": annotation_id,
                    "data": removed_annotation.to_dict()
                })
                self.redo_stack = []  # Redoスタックをクリア
                return True
        return False
    
    def update_annotation(self, annotation_id: str, updated_data: Dict[str, Any]) -> bool:
        """アノテーションを更新"""
        for i, annotation in enumerate(self.annotations):
            if annotation.id == annotation_id:
                # 更新前のデータを保存
                old_data = annotation.to_dict()
                
                # 更新
                for key, value in updated_data.items():
                    if hasattr(annotation, key):
                        setattr(annotation, key, value)
                
                # 操作履歴に追加
                self.history.append({
                    "action": "update",
                    "annotation_id": annotation_id,
                    "old_data": old_data,
                    "new_data": annotation.to_dict()
                })
                self.redo_stack = []  # Redoスタックをクリア
                return True
        return False
    
    def get_annotation(self, annotation_id: str) -> Optional[BoundingBox3D]:
        """指定IDのアノテーションを取得"""
        for annotation in self.annotations:
            if annotation.id == annotation_id:
                return annotation
        return None
    
    def get_all_annotations(self) -> List[BoundingBox3D]:
        """全てのアノテーションを取得"""
        return self.annotations
    
    def get_annotations_by_track(self, track_id: str) -> List[BoundingBox3D]:
        """指定のトラックIDに属するアノテーションを取得"""
        return [annotation for annotation in self.annotations if annotation.track_id == track_id]
    
    def set_frame_id(self, frame_id: str):
        """フレームIDを設定"""
        self.frame_id = frame_id
    
    def get_frame_id(self) -> str:
        """現在のフレームIDを取得"""
        return self.frame_id
    
    def save_to_file(self, file_path: str) -> bool:
        """アノテーションをJSONファイルに保存"""
        data = {
            "frame_id": self.frame_id,
            "annotations": [a.to_dict() for a in self.annotations]
        }
        
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"保存エラー: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'AnnotationManager':
        """JSONファイルからアノテーションをロード"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            manager = cls(frame_id=data.get("frame_id", "00000"))
            for annotation_data in data.get("annotations", []):
                bbox = BoundingBox3D.from_dict(annotation_data)
                manager.annotations.append(bbox)
            return manager
        except Exception as e:
            print(f"読み込みエラー: {e}")
            return cls()  # 空のマネージャーを返す
    
    def undo(self) -> bool:
        """直前の操作を取り消し"""
        if not self.history:
            return False
        
        last_action = self.history.pop()
        self.redo_stack.append(last_action)
        
        action_type = last_action["action"]
        annotation_id = last_action["annotation_id"]
        
        if action_type == "add":
            # 追加されたアノテーションを削除
            for i, annotation in enumerate(self.annotations):
                if annotation.id == annotation_id:
                    self.annotations.pop(i)
                    break
        
        elif action_type == "remove":
            # 削除されたアノテーションを復元
            annotation_data = last_action["data"]
            bbox = BoundingBox3D.from_dict(annotation_data)
            self.annotations.append(bbox)
        
        elif action_type == "update":
            # 更新前の状態に戻す
            old_data = last_action["old_data"]
            for i, annotation in enumerate(self.annotations):
                if annotation.id == annotation_id:
                    for key, value in old_data.items():
                        if hasattr(annotation, key):
                            setattr(annotation, key, value)
                    break
        
        return True
    
    def redo(self) -> bool:
        """取り消した操作をやり直し"""
        if not self.redo_stack:
            return False
        
        action = self.redo_stack.pop()
        self.history.append(action)
        
        action_type = action["action"]
        annotation_id = action["annotation_id"]
        
        if action_type == "add":
            # 削除されたアノテーションを再追加
            annotation_data = action["data"]
            bbox = BoundingBox3D.from_dict(annotation_data)
            self.annotations.append(bbox)
        
        elif action_type == "remove":
            # 復元されたアノテーションを再削除
            for i, annotation in enumerate(self.annotations):
                if annotation.id == annotation_id:
                    self.annotations.pop(i)
                    break
        
        elif action_type == "update":
            # 更新後の状態に戻す
            new_data = action["new_data"]
            for i, annotation in enumerate(self.annotations):
                if annotation.id == annotation_id:
                    for key, value in new_data.items():
                        if hasattr(annotation, key):
                            setattr(annotation, key, value)
                    break
        
        return True

class ClassManager:
    """クラスラベルの管理を行うクラス"""
    
    def __init__(self):
        self.classes: List[ClassLabel] = []
    
    def add_class(self, class_label: ClassLabel) -> bool:
        """クラスラベルを追加"""
        # IDが既に存在する場合は追加しない
        if any(c.id == class_label.id for c in self.classes):
            return False
        
        self.classes.append(class_label)
        return True
    
    def get_class(self, class_id: str) -> Optional[ClassLabel]:
        """指定IDのクラスラベルを取得"""
        for c in self.classes:
            if c.id == class_id:
                return c
        return None
    
    def get_all_classes(self) -> List[ClassLabel]:
        """全てのクラスラベルを取得"""
        return self.classes
    
    def save_to_file(self, file_path: str) -> bool:
        """クラスラベルをJSONファイルに保存"""
        data = {
            "classes": [c.to_dict() for c in self.classes]
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"保存エラー: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'ClassManager':
        """JSONファイルからクラスラベルをロード"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            manager = cls()
            for class_data in data.get("classes", []):
                class_label = ClassLabel.from_dict(class_data)
                manager.add_class(class_label)
            return manager
        except Exception as e:
            print(f"読み込みエラー: {e}")
            return cls()  # 空のマネージャーを返す 