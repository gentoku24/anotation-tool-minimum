import os
import json
from typing import Dict, List, Optional, Any, Tuple
import copy

from src.models import BoundingBox3D, AnnotationManager

class TrackingManager:
    """
    トラッキング情報を管理するクラス
    """
    
    def __init__(self):
        self.tracks = {}  # トラックID → {フレームID: アノテーションID}
        self.project_root = None  # プロジェクトのルートディレクトリ
    
    def set_project_root(self, directory: str):
        """
        プロジェクトのルートディレクトリを設定
        
        Args:
            directory: プロジェクトのルートディレクトリパス
        """
        self.project_root = directory
    
    def get_track_info_file_path(self) -> str:
        """
        トラック情報ファイルのパスを取得
        
        Returns:
            str: トラック情報ファイルのパス
        """
        if self.project_root is None:
            return ""
        
        return os.path.join(self.project_root, "track_info.json")
    
    def save_track_info(self) -> bool:
        """
        トラック情報をファイルに保存
        
        Returns:
            bool: 保存に成功したかどうか
        """
        if self.project_root is None:
            return False
        
        file_path = self.get_track_info_file_path()
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.tracks, f, indent=2)
            return True
        except Exception as e:
            print(f"トラック情報の保存エラー: {e}")
            return False
    
    def load_track_info(self) -> bool:
        """
        トラック情報をファイルから読み込み
        
        Returns:
            bool: 読み込みに成功したかどうか
        """
        if self.project_root is None:
            return False
        
        file_path = self.get_track_info_file_path()
        
        if not os.path.exists(file_path):
            return False
        
        try:
            with open(file_path, 'r') as f:
                self.tracks = json.load(f)
            return True
        except Exception as e:
            print(f"トラック情報の読み込みエラー: {e}")
            return False
    
    def add_annotation_to_track(self, track_id: str, frame_id: str, annotation_id: str) -> bool:
        """
        トラックにアノテーションを追加
        
        Args:
            track_id: トラックID
            frame_id: フレームID
            annotation_id: アノテーションID
            
        Returns:
            bool: 追加に成功したかどうか
        """
        if track_id not in self.tracks:
            self.tracks[track_id] = {}
        
        self.tracks[track_id][frame_id] = annotation_id
        return True
    
    def remove_annotation_from_track(self, track_id: str, frame_id: str) -> bool:
        """
        トラックからアノテーションを削除
        
        Args:
            track_id: トラックID
            frame_id: フレームID
            
        Returns:
            bool: 削除に成功したかどうか
        """
        if track_id not in self.tracks or frame_id not in self.tracks[track_id]:
            return False
        
        del self.tracks[track_id][frame_id]
        
        # トラックが空になった場合は削除
        if not self.tracks[track_id]:
            del self.tracks[track_id]
        
        return True
    
    def get_track_annotation_id(self, track_id: str, frame_id: str) -> Optional[str]:
        """
        指定したトラックとフレームのアノテーションIDを取得
        
        Args:
            track_id: トラックID
            frame_id: フレームID
            
        Returns:
            Optional[str]: アノテーションID、または存在しない場合はNone
        """
        if track_id not in self.tracks or frame_id not in self.tracks[track_id]:
            return None
        
        return self.tracks[track_id][frame_id]
    
    def get_all_tracks(self) -> List[str]:
        """
        全てのトラックIDを取得
        
        Returns:
            List[str]: トラックIDのリスト
        """
        return list(self.tracks.keys())
    
    def get_track_frames(self, track_id: str) -> List[str]:
        """
        指定したトラックに含まれるフレームIDを取得
        
        Args:
            track_id: トラックID
            
        Returns:
            List[str]: フレームIDのリスト
        """
        if track_id not in self.tracks:
            return []
        
        return list(self.tracks[track_id].keys())
    
    def propagate_annotations(self, annotation_manager: AnnotationManager, 
                              from_frame_id: str, to_frame_id: str) -> bool:
        """
        アノテーションを別のフレームに伝播
        
        Args:
            annotation_manager: 現在のフレームのアノテーションマネージャ
            from_frame_id: 伝播元のフレームID
            to_frame_id: 伝播先のフレームID
            
        Returns:
            bool: 伝播に成功したかどうか
        """
        if self.project_root is None:
            return False
        
        # 伝播先のフレームディレクトリを確認
        to_frame_dir = os.path.join(self.project_root, "frames", f"frame_{to_frame_id}")
        if not os.path.exists(to_frame_dir):
            os.makedirs(to_frame_dir, exist_ok=True)
        
        # 伝播先のアノテーションファイル
        to_annotation_file = os.path.join(to_frame_dir, "annotations.json")
        
        # 伝播先のアノテーションマネージャを準備
        to_manager = AnnotationManager.load_from_file(to_annotation_file) if os.path.exists(to_annotation_file) else AnnotationManager(frame_id=to_frame_id)
        
        # 伝播元のアノテーションをコピー
        for annotation in annotation_manager.get_all_annotations():
            # トラックIDを取得
            track_id = annotation.track_id
            
            # 伝播先のフレームに同じtrack_idを持つアノテーションがあるか確認
            existing_annotation = None
            existing_annotation_id = None
            
            for existing in to_manager.get_all_annotations():
                if existing.track_id == track_id:
                    existing_annotation = existing
                    existing_annotation_id = existing.id
                    break
            
            if existing_annotation:
                # 既存のアノテーションを更新
                updated_data = {
                    "center": annotation.center.copy(),
                    "size": annotation.size.copy(),
                    "rotation": annotation.rotation.copy(),
                    "class_id": annotation.class_id,
                    "class_label": annotation.class_label,
                    "class_color": annotation.class_color.copy()
                }
                
                to_manager.update_annotation(existing_annotation_id, updated_data)
                
                # トラッキング情報は既に存在するので更新不要
            else:
                # 新しいアノテーションを作成
                # ディープコピーを作成
                new_annotation = copy.deepcopy(annotation)
                
                # 必ず新しいIDを生成するために明示的にNoneを設定
                # BoundingBox3Dクラスのコンストラクタで新しいIDが自動生成される
                new_annotation.id = None
                
                # トラックIDは維持
                new_annotation.track_id = track_id
                
                # 伝播先のフレームに追加
                new_annotation_id = to_manager.add_annotation(new_annotation)
                
                # トラッキング情報を更新
                self.add_annotation_to_track(track_id, to_frame_id, new_annotation_id)
        
        # 伝播先のアノテーションを保存
        if not to_manager.save_to_file(to_annotation_file):
            return False
        
        # トラック情報も保存
        return self.save_track_info() 