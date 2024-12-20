# ベースイメージ
FROM python:3.11.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY . /app

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションを起動
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
