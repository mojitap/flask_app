# MojiTap

## サービス概要
MojiTapは、名誉毀損・誹謗中傷・人権侵害のリスクを簡単に調査できる検索サービスです。

## 必要な環境設定
`.env`ファイルに以下の環境変数を追加してください：

```plaintext
DROPBOX_DIFFERENCE_URL=your-dropbox-difference-url
DROPBOX_MODEL_URL=your-dropbox-model-url
DROPBOX_OFFENSIVE_WORDS_URL=your-dropbox-offensive-words-url
DATABASE_URL=sqlite:///database.db
