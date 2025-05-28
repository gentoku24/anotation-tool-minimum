# 3Dアノテーションツール

点群データに3Dバウンディングボックスを付けるためのアノテーションツールです。

## 機能

- 点群データの読み込みと表示
- 3Dバウンディングボックスの作成、編集、削除
- アノテーションの保存とロード
- クラスラベルの管理
- **NEW**: Support for continuous frame sequences
- **NEW**: Annotation propagation between frames

## インストール方法

### 通常のインストール
1. リポジトリをクローン
2. 依存パッケージのインストール
```
pip install -r requirements.txt
```

### Dockerを使用する場合
1. Dockerをインストール
2. Windowsの場合はX serverをインストール（VcXsrv等）
3. 以下のいずれかの方法で実行:

#### ローカルでビルドする場合
```
docker-compose build
docker-compose up
```

#### Docker Hubからプルする場合
docker-compose.ymlファイル内の以下の行のコメントを入れ替えます:
```
# ローカルビルドの場合
# build: .
# Docker Hubからのプルを使用する場合はこちらを有効化
image: gentoku24/anotation-tool:latest
```

または、特定バージョンを使用する場合：
```
# ローカルビルドの場合
# build: .
# Docker Hubからのプルを使用する場合はこちらを有効化
# image: gentoku24/anotation-tool:latest
# 特定バージョンを使用する場合はこちらを有効化
image: gentoku24/anotation-tool:v1.0-20250528
```

その後、以下のコマンドを実行:
```
docker-compose up
```

## 使用方法

### 通常の実行
```
python -m src.main
```

### Dockerでの実行
Windowsの場合：
1. X serverを起動（VcXsrvの場合、「-ac -nowgl」オプションを付けて起動）
2. 以下のコマンドで実行
```
docker-compose up
```

または、提供されているバッチファイルを使用：
```
run_docker_windows.bat
```

## データ構造

- `/data` - 点群データと保存されたアノテーションが格納されます
- `/class_labels` - クラスラベルの定義が格納されます
- `/src` - ソースコードが格納されます 

## フレーム管理機能

### Organizing Multi-frame Data
The tool now supports continuous frame sequences with this directory structure:
- A top-level `frames/` directory contains subdirectories for each frame
- Each frame directory is named `frame_XXXXX` (where XXXXX is a 5-digit frame ID)
- Each frame directory contains a point cloud file and an annotations.json file
- A `track_info.json` file in the project root maintains tracking information

### Keyboard Shortcuts
- Left Arrow: Go to previous frame
- Right Arrow: Go to next frame
- G: Go to a specific frame
- P: Propagate annotations to the next frame

### Working with Frame Sequences
1. Use "Open Sequence" to select a project directory
2. Navigate between frames using the Previous/Next buttons or keyboard shortcuts
3. Use "Propagate to Next Frame" to copy annotations to the next frame
4. All annotations are saved automatically when switching frames

## データフォーマット

### Annotation File Format
```json
{
  "frame_id": "00001",
  "annotations": [
    {
      "id": "20250607123456789",
      "class_id": "car_01",
      "class_label": "car",
      "class_color": [255, 0, 0],
      "center": [0.0, 0.0, 0.0],
      "size": [2.0, 4.0, 1.5],
      "rotation": [0.0, 0.0, 0.0],
      "track_id": "20250607123456789"
    }
  ]
}
```

### Track Information File Format
```json
{
  "track_20250607123456789": {
    "00000": "20250607123456789",
    "00001": "20250607123457123",
    "00002": "20250607123458456"
  }
}
```
