import numpy as np
import math
from typing import List, Tuple, Dict, Any, Optional
import struct
from src.logger import logger

def load_point_cloud(file_path: str) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """点群データを読み込む"""
    try:
        # ファイル拡張子に基づいて適切な読み込み関数を選択
        if file_path.endswith('.npy'):
            # NumPy配列ファイルを読み込み
            xyz = np.load(file_path)
            logger.log_change(f"NumPyファイルを読み込み: {file_path}")
            return xyz, xyz
        elif file_path.endswith('.pcd'):
            points = []
            header = {}
            data_format = None
            header_lines = []
            with open(file_path, 'rb') as f:
                # ヘッダーをバイトで読み込む
                while True:
                    line = f.readline()
                    if not line:
                        break
                    header_lines.append(line)
                    try:
                        line_str = line.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        # バイナリデータに到達したら終了
                        break
                    if line_str.startswith('#'):
                        continue
                    if ' ' in line_str:
                        key, value = line_str.split(' ', 1)
                        header[key] = value
                        if key == 'DATA':
                            data_format = value
                            break
                header_end = f.tell()
                if data_format == 'ascii':
                    for line in f:
                        if line.strip():
                            values = line.decode('utf-8').strip().split()
                            x, y, z = map(float, values[:3])
                            points.append([x, y, z])
                elif data_format == 'binary':
                    num_points = int(header.get('POINTS', 0))
                    f.seek(header_end)
                    for _ in range(num_points):
                        x, y, z = struct.unpack('fff', f.read(12))
                        points.append([x, y, z])
                else:
                    error_msg = f"未対応のデータ形式: {data_format}"
                    logger.log_error(error_msg)
                    print(error_msg)
                    return None, None
            xyz = np.array(points)
            logger.log_change(f"PCDファイルを読み込み: {file_path} (形式: {data_format}, 点数: {len(points)})")
            return xyz, xyz
        else:
            error_msg = f"未対応のファイル形式: {file_path}"
            logger.log_error(error_msg)
            print(error_msg)
            return None, None
    except Exception as e:
        error_msg = f"点群読み込みエラー: {str(e)}"
        logger.log_error(error_msg, e)
        print(error_msg)
        return None, None 