import pandas as pd

# データの読み込み
df = pd.read_csv('articles.csv')
print("Original data loaded")

# 重複する行を削除
df = df.drop_duplicates()
print("Duplicates removed")

# クリーンなデータを新しいCSVに保存
df.to_csv('cleaned_data.csv', index=False)
print("Cleaned data saved to cleaned_data.csv")
