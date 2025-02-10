# MojiTap

## サービス概要
MojiTapは、名誉毀損・誹謗中傷・人権侵害のリスクを簡単に調査できる検索サービスです。

## 必要な環境設定
本サービスを実行するために、プロジェクトルートに `.env` ファイルを作成し、以下の環境変数を設定してください。

# Dropbox URLs
DROPBOX_OFFENSIVE_WORDS_URL=your-dropbox-offensive-words-url
DROPBOX_SURNAMES_URL=your-dropbox-surnames-url

# データベース設定
DATABASE_URL=sqlite:///database.db

# セキュリティ設定
SECRET_KEY=your_secret_key_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Twitter OAuth
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
