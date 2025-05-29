import numpy as np

# 座標変換の設定
# Trueに設定すると、load_point_cloud時に座標変換が適用されます
ENABLE_COORDINATE_TRANSFORM = True

# 座標系の種類
COORDINATE_SYSTEMS = {
    'standard': {
        'description': '標準座標系 (X: 前, Y: 左, Z: 上)',
        'axes': ['X: 前方向', 'Y: 左方向', 'Z: 上方向']
    },
    'your_lidar': {
        'description': 'カスタムLiDAR座標系',
        'axes': ['X: 右方向', 'Y: 前方向', 'Z: 上方向']  # 例：この座標系を実際のLiDARに合わせて調整してください
    }
    # 必要に応じて他の座標系を追加
}

# デフォルト設定
DEFAULT_SOURCE_SYSTEM = 'your_lidar'
DEFAULT_TARGET_SYSTEM = 'standard'

def transform_coordinates(xyz, from_system=DEFAULT_SOURCE_SYSTEM, to_system=DEFAULT_TARGET_SYSTEM):
    """座標系間の変換を行う関数
    
    Args:
        xyz (numpy.ndarray): 変換する座標データ (N, 3)
        from_system (str): 元の座標系
        to_system (str): 変換先の座標系
        
    Returns:
        numpy.ndarray: 変換後の座標データ
    """
    if xyz is None:
        return None
    
    # 同じ座標系なら変換不要
    if from_system == to_system or not ENABLE_COORDINATE_TRANSFORM:
        return xyz
    
    # コピーを作成して変換
    transformed = xyz.copy()
    
    # your_lidar → standard の変換
    if from_system == 'your_lidar' and to_system == 'standard':
        # ここで必要な座標変換を実装
  
        transformed[:, 0] = xyz[:, 0]  
        transformed[:, 1] = -xyz[:, 2]  
        transformed[:, 2] = -xyz[:, 1]  
        
        # 必要に応じて軸の正負を反転させる
        # transformed[:, 0] = -transformed[:, 0]  # X軸反転
        
        return transformed
    
    # standard → your_lidar の変換 (逆変換)
    if from_system == 'standard' and to_system == 'your_lidar':
        # 逆変換を実装
        #transformed[:, 2] = xyz[:, 0]  # 新しいZ = 古いX
        #transformed[:, 0] = xyz[:, 2]  # 新しいX = 古いZ
        # Y軸はそのまま
        
        # 必要に応じて軸の反転を元に戻す
        # transformed[:, 0] = -transformed[:, 0]  # X軸反転を戻す
        
        return transformed
    
    # その他の変換ケースが必要な場合はここに追加
    
    # 未定義の変換の場合は変換なしで返す
    print(f"警告: 未定義の座標変換 {from_system} → {to_system}")
    return xyz

def is_transform_enabled():
    """座標変換が有効かどうかを返す"""
    return ENABLE_COORDINATE_TRANSFORM

def enable_transform(enable=True):
    """座標変換の有効/無効を切り替える"""
    global ENABLE_COORDINATE_TRANSFORM
    ENABLE_COORDINATE_TRANSFORM = enable
    return ENABLE_COORDINATE_TRANSFORM

def get_available_systems():
    """利用可能な座標系のリストを返す"""
    return list(COORDINATE_SYSTEMS.keys())

def get_system_info(system_name):
    """指定された座標系の情報を返す"""
    if system_name in COORDINATE_SYSTEMS:
        return COORDINATE_SYSTEMS[system_name]
    return None 