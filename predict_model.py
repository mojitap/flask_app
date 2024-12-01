import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

# DistilBERTのトークナイザーとモデルをロード
tokenizer = DistilBertTokenizer.from_pretrained('./fine_tuned_bert')
model = DistilBertForSequenceClassification.from_pretrained('./fine_tuned_bert')

# テスト用のテキスト
test_texts = ["B社の製品には問題があります。", "今日は楽しい一日だった。"]

# テキストをトークナイズ
test_encodings = tokenizer(test_texts, padding=True, truncation=True, return_tensors='pt')

# モデルで予測
outputs = model(**test_encodings)

# ログitsから予測を取得
predictions = torch.argmax(outputs.logits, dim=1)

# 結果を表示
for text, prediction in zip(test_texts, predictions):
    label = "ポジティブ" if prediction == 0 else "ネガティブ"
    print(f"テキスト: {text} -> 判定: {label}")
