import os
import glob
import re
from typing import List, Dict, Optional, Tuple

class FrameManager:
    """
    フレームシーケンスを管理するクラス
    """
    
    def __init__(self):
        self.frames = {}  # フレームID → フレームデータ(点群ファイルパス)
        self.current_frame_id = None
        self.frame_sequence = []  # フレームの順序（ソート済みフレームIDのリスト）
        self.project_root = None  # プロジェクトのルートディレクトリ
    
    def load_sequence(self, directory: str) -> bool:
        """
        ディレクトリからフレームシーケンスを読み込む
        
        Args:
            directory: フレームが格納されているディレクトリパス
            
        Returns:
            bool: 読み込みに成功したかどうか
        """
        self.project_root = directory
        frames_dir = os.path.join(directory, "frames")
        
        # framesディレクトリが存在しない場合は作成
        if not os.path.exists(frames_dir):
            os.makedirs(frames_dir, exist_ok=True)
            return False
        
        # フレームディレクトリを検索
        frame_dirs = glob.glob(os.path.join(frames_dir, "frame_*"))
        
        if not frame_dirs:
            return False
        
        self.frames = {}
        self.frame_sequence = []
        
        # 各フレームディレクトリから点群ファイルを検索
        for frame_dir in frame_dirs:
            frame_id = os.path.basename(frame_dir).replace("frame_", "")
            
            # 点群ファイルを検索
            pcd_files = glob.glob(os.path.join(frame_dir, "*.pcd"))
            if pcd_files:
                self.frames[frame_id] = pcd_files[0]  # 最初の.pcdファイルを使用
                self.frame_sequence.append(frame_id)
        
        # フレームシーケンスを番号順にソート
        self.frame_sequence.sort(key=lambda x: int(x))
        
        # 現在のフレームを設定
        if self.frame_sequence:
            self.current_frame_id = self.frame_sequence[0]
            return True
        
        return False
    
    def create_frame_structure(self, directory: str, num_frames: int = 10) -> bool:
        """
        フレーム構造を新規作成する（テスト/開発用）
        
        Args:
            directory: プロジェクトのルートディレクトリ
            num_frames: 作成するフレーム数
            
        Returns:
            bool: 作成に成功したかどうか
        """
        self.project_root = directory
        frames_dir = os.path.join(directory, "frames")
        
        # ディレクトリを作成
        os.makedirs(frames_dir, exist_ok=True)
        
        # 各フレームのディレクトリを作成
        for i in range(num_frames):
            frame_id = f"{i:05d}"
            frame_dir = os.path.join(frames_dir, f"frame_{frame_id}")
            os.makedirs(frame_dir, exist_ok=True)
        
        return True
    
    def get_current_frame(self) -> Optional[str]:
        """
        現在のフレームの点群ファイルパスを取得
        
        Returns:
            Optional[str]: 点群ファイルのパス、またはNone
        """
        if self.current_frame_id is None or self.current_frame_id not in self.frames:
            return None
        
        return self.frames[self.current_frame_id]
    
    def get_current_frame_id(self) -> Optional[str]:
        """
        現在のフレームIDを取得
        
        Returns:
            Optional[str]: 現在のフレームID、またはNone
        """
        return self.current_frame_id
    
    def get_annotation_file_path(self, frame_id: Optional[str] = None) -> str:
        """
        フレームIDに対応するアノテーションファイルのパスを取得
        
        Args:
            frame_id: フレームID（Noneの場合は現在のフレームを使用）
            
        Returns:
            str: アノテーションファイルのパス
        """
        frame_id = frame_id or self.current_frame_id
        if frame_id is None:
            return ""
        
        frame_dir = os.path.join(self.project_root, "frames", f"frame_{frame_id}")
        return os.path.join(frame_dir, "annotations.json")
    
    def next_frame(self) -> Optional[str]:
        """
        次のフレームに移動
        
        Returns:
            Optional[str]: 次のフレームの点群ファイルパス、またはNone
        """
        if not self.frame_sequence or self.current_frame_id is None:
            return None
        
        # 現在のフレームのインデックスを取得
        try:
            current_index = self.frame_sequence.index(self.current_frame_id)
        except ValueError:
            return None
        
        # 次のフレームのインデックスを計算
        next_index = (current_index + 1) % len(self.frame_sequence)
        
        # 次のフレームIDを設定
        self.current_frame_id = self.frame_sequence[next_index]
        
        return self.get_current_frame()
    
    def prev_frame(self) -> Optional[str]:
        """
        前のフレームに移動
        
        Returns:
            Optional[str]: 前のフレームの点群ファイルパス、またはNone
        """
        if not self.frame_sequence or self.current_frame_id is None:
            return None
        
        # 現在のフレームのインデックスを取得
        try:
            current_index = self.frame_sequence.index(self.current_frame_id)
        except ValueError:
            return None
        
        # 前のフレームのインデックスを計算
        prev_index = (current_index - 1) % len(self.frame_sequence)
        
        # 前のフレームIDを設定
        self.current_frame_id = self.frame_sequence[prev_index]
        
        return self.get_current_frame()
    
    def goto_frame(self, frame_id: str) -> Optional[str]:
        """
        指定したフレームIDに移動
        
        Args:
            frame_id: 移動先のフレームID
            
        Returns:
            Optional[str]: 指定したフレームの点群ファイルパス、またはNone
        """
        if frame_id not in self.frames:
            return None
        
        self.current_frame_id = frame_id
        return self.get_current_frame()
    
    def get_frame_count(self) -> int:
        """
        フレームの総数を取得
        
        Returns:
            int: フレームの総数
        """
        return len(self.frame_sequence)
    
    def get_all_frame_ids(self) -> List[str]:
        """
        全てのフレームIDを取得
        
        Returns:
            List[str]: ソートされたフレームIDのリスト
        """
        return self.frame_sequence.copy()
    
    def import_point_cloud(self, src_file_path: str, frame_id: str) -> bool:
        """
        点群ファイルをフレーム構造にインポート
        
        Args:
            src_file_path: インポートする点群ファイルのパス
            frame_id: インポート先のフレームID
            
        Returns:
            bool: インポートに成功したかどうか
        """
        if not os.path.exists(src_file_path):
            return False
        
        # フレームディレクトリを作成/確認
        frame_dir = os.path.join(self.project_root, "frames", f"frame_{frame_id}")
        os.makedirs(frame_dir, exist_ok=True)
        
        # ファイル名を維持しつつコピー
        dest_file = os.path.join(frame_dir, os.path.basename(src_file_path))
        
        try:
            # ファイルをコピー
            with open(src_file_path, 'rb') as src, open(dest_file, 'wb') as dst:
                dst.write(src.read())
            
            # フレームリストを更新
            self.frames[frame_id] = dest_file
            
            # フレームシーケンスに追加（まだ含まれていない場合）
            if frame_id not in self.frame_sequence:
                self.frame_sequence.append(frame_id)
                self.frame_sequence.sort(key=lambda x: int(x))
            
            return True
        except Exception as e:
            print(f"インポートエラー: {e}")
            return False
    
    def clear(self) -> None:
        """
        内部状態をリセットする
        """
        self.frames = {}
        self.current_frame_id = None
        self.frame_sequence = []
        # プロジェクトルートは保持する 