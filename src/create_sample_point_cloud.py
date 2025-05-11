#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import os

def create_dummy_point_cloud(num_points=10000, file_name="sample_point_cloud.npy"):
    """ダミーの点群データを作成してファイルに保存する"""
    # ランダムな点群を生成
    points = np.random.rand(num_points, 3) * 20 - 10  # -10から10の範囲
    
    # 道路形状を模したZ座標の調整
    points[:, 2] = points[:, 2] * 0.2 - 1.5  # 地面は大体 z = -1.5 付近
    
    # 一部の点を数個の塊にして車両や歩行者を模倣
    # 車両1
    car1_center = np.array([3.0, 5.0, -1.0])
    car1_points = np.random.rand(500, 3) * np.array([2.0, 4.0, 1.5]) - np.array([1.0, 2.0, 0.75])
    car1_points += car1_center
    
    # 車両2
    car2_center = np.array([-4.0, -3.0, -1.0])
    car2_points = np.random.rand(400, 3) * np.array([2.0, 4.0, 1.5]) - np.array([1.0, 2.0, 0.75])
    car2_points += car2_center
    
    # 歩行者1
    ped1_center = np.array([1.0, -2.0, -0.5])
    ped1_points = np.random.rand(100, 3) * np.array([0.6, 0.6, 1.8]) - np.array([0.3, 0.3, 0.0])
    ped1_points += ped1_center
    
    # すべての点を結合
    all_points = np.vstack([points, car1_points, car2_points, ped1_points])
    
    # ファイルに保存
    output_path = os.path.join("data", file_name)
    os.makedirs("data", exist_ok=True)
    
    np.save(output_path, all_points)
    print(f"点群を保存しました: {output_path}")
    
    return output_path

if __name__ == "__main__":
    file_path = create_dummy_point_cloud()
    
    # 保存したデータを読み込み確認
    point_cloud = np.load(file_path)
    print(f"点群データ形状: {point_cloud.shape}")
    print(f"点群データの範囲: X[{point_cloud[:, 0].min():.2f}, {point_cloud[:, 0].max():.2f}], "
          f"Y[{point_cloud[:, 1].min():.2f}, {point_cloud[:, 1].max():.2f}], "
          f"Z[{point_cloud[:, 2].min():.2f}, {point_cloud[:, 2].max():.2f}]") 