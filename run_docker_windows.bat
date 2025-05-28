@echo off
echo Dockerコンテナを起動します

rem X Server（VcXsrv）が起動していることを確認してください
echo X Serverが起動していることを確認してください
echo （VcXsrvを使用する場合は、-ac オプションを付けて起動してください）

rem DISPLAY環境変数を設定
set DISPLAY=127.0.0.1:0.0

rem Dockerコンテナをビルドして起動
docker-compose build
docker-compose up

echo 完了しました
pause 