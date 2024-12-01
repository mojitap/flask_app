import pandas as pd
import mojimoji
import re

# CSVファイルからデータを読み込む
df = pd.read_csv('cleaned_data.csv')
print(df.columns)

# 半角に変換
df['Content'] = df['Content'].apply(lambda x: mojimoji.han_to_zen(x))

# 記号を削除
df['Content'] = df['Content'].apply(lambda x: re.sub(r'[^\w\s]', '', x))

# 正規化後のデータを新しいCSVに保存
df.to_csv('normalized_data.csv', index=False)
