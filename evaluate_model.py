import re
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

# 前処理関数（既に定義されている場合）
def preprocess_text(text):
    text = re.sub(r'[「」]', '', text)
    text = text.strip()
    return text

# データの読み込みと前処理
data = pd.read_csv('data/normalized_data.csv')
data['Content'] = data['Content'].apply(preprocess_text)


# テストデータの準備
test_texts = data['Content'].tolist()
test_labels = [0 if 'ネガティブ' in text else 1 for text in data['Content']]  # ラベルの設定例

# モデルとトークナイザーのロード
model = DistilBertForSequenceClassification.from_pretrained('./fine_tuned_bert')
tokenizer = DistilBertTokenizer.from_pretrained('./fine_tuned_bert')

# テストデータのエンコード
encodings = tokenizer(test_texts, return_tensors='pt', padding=True, truncation=True, max_length=512)

# モデルを評価モードに設定
model.eval()

# 予測の取得
with torch.no_grad():
    outputs = model(**encodings)
    logits = outputs.logits
    predictions = torch.argmax(logits, dim=1).cpu().numpy()

# 評価指標の計算
accuracy = accuracy_score(test_labels, predictions)
f1 = f1_score(test_labels, predictions)
precision = precision_score(test_labels, predictions)
recall = recall_score(test_labels, predictions)

# 結果の表示
print(f'Accuracy: {accuracy:.4f}')
print(f'F1 Score: {f1:.4f}')
print(f'Precision: {precision:.4f}')
print(f'Recall: {recall:.4f}')
