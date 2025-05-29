import os
import sys
import random
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from PySide6.QtGui import QImage
import traceback

# ログユーティリティをインポート
from src.logger import logger
from src.coordinate_transform import transform_coordinates, is_transform_enabled

def load_point_cloud(file_path: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """点群ファイルを読み込む
    
    Args:
        file_path: 点群ファイルのパス
        
    Returns:
        Tuple[np.ndarray, np.ndarray]: (xyz座標のみの点群, 全データの点群)
    """
    try:
        if not os.path.exists(file_path):
            logger.log_error(f"点群ファイルが存在しません: {file_path}")
            print(f"エラー: 点群ファイルが存在しません: {file_path}")
            return None, None
            
        if file_path.endswith('.npy'):
            try:
                # NumPy形式
                point_cloud = np.load(file_path)
                # 点群データのフォーマットを確認
                if len(point_cloud.shape) == 1:
                    # 1次元配列の場合は形状を変換
                    point_count = point_cloud.shape[0] // 3
                    point_cloud = point_cloud.reshape(point_count, 3)
                elif len(point_cloud.shape) == 2:
                    # 既に適切な形状の場合はそのまま使用
                    pass
                else:
                    # 不適切な形状の場合はエラー
                    logger.log_error(f"不適切な点群データ形状: {point_cloud.shape}")
                    print(f"エラー: 不適切な点群データ形状: {point_cloud.shape}")
                    return None, None
                
                # xyz座標のみの点群データを取得
                if point_cloud.shape[1] >= 3:
                    point_cloud_xyz = point_cloud[:, :3]
                else:
                    logger.log_error(f"点群データに3次元座標が含まれていません: {point_cloud.shape}")
                    print(f"エラー: 点群データに3次元座標が含まれていません: {point_cloud.shape}")
                    return None, None
                
                print(f"NumPyファイルを読み込みました: {file_path}, 形状={point_cloud.shape}")
            except Exception as e:
                logger.log_error(f"NumPyファイルの読み込みに失敗: {file_path}", e)
                print(f"エラー: NumPyファイルの読み込みに失敗: {file_path}, {str(e)}")
                traceback.print_exc()
                return None, None
        elif file_path.endswith('.pcd'):
            try:
                # PCDファイルの独自読み込み処理
                header = {}
                data_format = None
                data_type = None
                point_count = 0
                fields = []
                sizes = []
                types = []
                counts = []
                width = 0
                height = 0
                points_list = []  # リストとして点を保存
                
                with open(file_path, 'rb') as f:
                    # ヘッダー情報を読み込む
                    line_count = 0
                    header_end = 0
                    is_binary = False
                    
                    for line in f:
                        line_count += 1
                        try:
                            line_str = line.decode('utf-8').strip()
                            if not line_str or line_str.startswith('#'):
                                continue
                                
                            # ヘッダー情報を解析
                            if ' ' in line_str:
                                key, value = line_str.split(' ', 1)
                                header[key] = value
                                
                                # 点の数と形式を記録
                                if key == 'POINTS':
                                    point_count = int(value)
                                elif key == 'WIDTH':
                                    width = int(value)
                                elif key == 'HEIGHT':
                                    height = int(value)
                                elif key == 'FIELDS':
                                    fields = value.split()
                                elif key == 'SIZE':
                                    sizes = [int(s) for s in value.split()]
                                elif key == 'TYPE':
                                    types = value.split()
                                elif key == 'COUNT':
                                    counts = [int(c) for c in value.split()]
                                
                                # データ形式を確認
                                if key == 'DATA':
                                    data_format = value
                                    if value == 'binary':
                                        is_binary = True
                                    header_end = f.tell()  # データ部分の開始位置を記録
                                    break
                        except UnicodeDecodeError:
                            # バイナリデータに到達したら終了
                            is_binary = True
                            break
                    
                    # データ形式に基づいて点群を読み込む
                    if data_format == 'ascii':
                        for line in f:
                            try:
                                line_str = line.decode('utf-8').strip()
                                if line_str:
                                    values = line_str.split()
                                    if len(values) >= 3:
                                        x, y, z = map(float, values[:3])
                                        points_list.append([x, y, z])
                            except Exception:
                                continue
                    elif data_format == 'binary' or is_binary:
                        # ファイルを最初から読み直す
                        f.seek(0)
                        header_text = b''
                        binary_start = 0
                        
                        # ヘッダーの終わりを見つける
                        for line in f:
                            header_text += line
                            if b'DATA binary' in line:
                                binary_start = f.tell()
                                break
                        
                        # バイナリデータを読み込む
                        f.seek(binary_start)
                        
                        # 単純に最初の3つのfloat値（x, y, z）を取得する
                        # 実際のフォーマットはヘッダーに基づいて解析する必要がありますが、簡略化します
                        point_size = sum(sizes)
                        for i in range(point_count):
                            try:
                                point_data = f.read(point_size)
                                if len(point_data) < 12:  # 最低3つのfloat値（12バイト）が必要
                                    break
                                
                                # 最初の3つのfloat値を取得
                                x = np.frombuffer(point_data[:4], dtype=np.float32)[0]
                                y = np.frombuffer(point_data[4:8], dtype=np.float32)[0]
                                z = np.frombuffer(point_data[8:12], dtype=np.float32)[0]
                                
                                points_list.append([x, y, z])
                            except Exception as e:
                                continue
                
                # NumPy配列に変換
                if len(points_list) == 0:
                    error_msg = f"PCDファイルからデータを読み込めませんでした: {file_path}"
                    logger.log_error(error_msg)
                    print(f"エラー: {error_msg}")
                    return None, None
                
                point_cloud = np.array(points_list)
                point_cloud_xyz = point_cloud.copy()
            except Exception as e:
                logger.log_error(f"PCDファイルの読み込みに失敗: {file_path}", e)
                print(f"エラー: PCDファイルの読み込みに失敗: {file_path}, {str(e)}")
                traceback.print_exc()
                return None, None
        else:
            logger.log_error(f"対応していないファイル形式です: {file_path}")
            print(f"エラー: 対応していないファイル形式です（.npyまたは.pcdのみサポート）: {file_path}")
            return None, None
        
        # 座標変換を適用
        if is_transform_enabled():
            try:
                transformed_xyz = transform_coordinates(point_cloud_xyz)
                logger.log_change(f"点群データに座標変換を適用しました: {file_path}")
                point_cloud_xyz = transformed_xyz
            except Exception as e:
                logger.log_error(f"座標変換中にエラーが発生: {file_path}", e)
                print(f"警告: 座標変換中にエラーが発生しましたが、元のデータを使用します: {str(e)}")
                traceback.print_exc()
                # 変換に失敗しても元のデータを返す
        
        logger.log_change(f"点群データを読み込みました: {file_path}")
        return point_cloud_xyz, point_cloud
    
    except Exception as e:
        logger.log_error(f"点群データの読み込みに失敗しました: {str(e)}", e)
        print(f"エラー: 点群データの読み込みに失敗しました: {str(e)}")
        traceback.print_exc()
        return None, None

def get_image_file_path(point_cloud_file: str) -> str:
    """点群ファイルに対応する画像ファイルのパスを取得"""
    dir_path = os.path.dirname(point_cloud_file)
    file_name = os.path.splitext(os.path.basename(point_cloud_file))[0]
    
    # 同一ディレクトリ内の任意の画像ファイルを検索
    for ext in ['.bmp', '.jpg', '.jpeg', '.png']:
        for file in os.listdir(dir_path):
            if file.lower().endswith(ext):
                img_path = os.path.join(dir_path, file)
                return img_path
    
    # 一致する画像が見つからない場合は空文字を返す
    return ""

def load_image(file_path: str) -> Optional[QImage]:
    """画像ファイルを読み込む"""
    try:
        image = QImage(file_path)
        
        if image.isNull():
            logger.log_error(f"画像ファイルの読み込みに失敗: {file_path}")
            return None
        
        logger.log_change(f"画像ファイルを読み込み: {file_path}")
        return image
    except Exception as e:
        logger.log_error(f"画像ファイル読み込みエラー: {str(e)}", e)
        return None

# def generate_random_color() -> List[int]:
#     """ランダムな色を生成"""
#     return [random.randint(0, 255) for _ in range(3)]

def ensure_directory_exists(directory_path: str) -> bool:
    """ディレクトリが存在することを確認し、存在しなければ作成"""
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        return True
    except Exception as e:
        logger.log_error(f"ディレクトリの作成に失敗: {directory_path}", e)
        return False 