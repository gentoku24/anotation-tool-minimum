# Python 3.9をベースイメージとして使用
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxkbcommon0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxcb-shape0 \
    # X11関連のパッケージを追加
    libx11-xcb1 \
    libxcb1 \
    libsm6 \
    # OpenGL関連のライブラリを追加
    libegl1 \
    libegl1-mesa \
    libgl1-mesa-dri \
    libglu1-mesa \
    libglx-mesa0 \
    libglx0 \
    libglvnd0 \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# データディレクトリを作成
RUN mkdir -p data class_labels logs

# PYTHONPATHを設定
ENV PYTHONPATH=/app

# PySide6のOpenGL設定
ENV QT_QPA_PLATFORM=xcb
ENV QT_XCB_GL_INTEGRATION=none

# コンテナ起動時のコマンド
CMD ["python", "src/main.py"] 