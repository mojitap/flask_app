import pandas as pd

# CSVファイルからデータを読み込む
df = pd.read_csv('articles.csv')

# クリーニング: 不要な部分を削除（例: 著作権情報や空白行）
df['Content'] = df['Content'].str.replace(r'Copyright ©.*', '', regex=True)  # 著作権情報を削除
df['Content'] = df['Content'].str.strip()  # 余分な空白を削除

# クリーニング後のデータを確認
print(df.head())

# データを保存（必要に応じてクリーニング後に再保存）
df.to_csv('cleaned_articles.csv', index=False)
