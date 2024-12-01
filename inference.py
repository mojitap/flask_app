from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import torch

# トレーニング済みモデルとトークナイザをロード
model = DistilBertForSequenceClassification.from_pretrained('./fine_tuned_bert')
tokenizer = DistilBertTokenizer.from_pretrained('./fine_tuned_bert')

# 推論するためのテストデータ
test_texts = ["テスト用の文章です。", "これは別のテスト文章です。"]

# テキストをトークナイズ
inputs = tokenizer(test_texts, padding=True, truncation=True, return_tensors="pt")

# モデルで予測
with torch.no_grad():
    outputs = model(**inputs)

# ログitsから予測を取得
predictions = torch.argmax(outputs.logits, dim=1)

# 結果を表示
for text, prediction in zip(test_texts, predictions):
    label = "ポジティブ" if prediction == 1 else "ネガティブ"
    print(f"テキスト: {text} -> 判定: {label}")
