# 3Dアノテーションツール

点群データに3Dバウンディングボックスを付けるためのアノテーションツールです。

## 機能

- 点群データの読み込みと表示
- 3Dバウンディングボックスの作成、編集、削除
- アノテーションの保存とロード
- クラスラベルの管理

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
