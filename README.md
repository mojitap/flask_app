# MojiTap

## サービス概要
MojiTapは、名誉毀損・誹謗中傷・人権侵害のリスクを簡単に調査できる検索サービスです。

## 必要な環境設定
`.env`ファイルに以下の環境変数を追加してください：

```plaintext
DROPBOX_OFFENSIVE_WORDS_URL=your-dropbox-offensive-words-url
DROPBOX_SURNAMES_URL=your-dropbox-surnames-url
DATABASE_URL=sqlite:///database.db
