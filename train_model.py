import re
import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, Trainer, TrainingArguments
import torch
from torch.utils.data import Dataset

# 前処理関数の定義
def preprocess_text(text):
    text = re.sub(r'[「」]', '', text)
    text = text.strip()
    return text

# データの読み込みと前処理
data = pd.read_csv('data/normalized_data.csv')
data['Content'] = data['Content'].apply(preprocess_text)

# 訓練データとテストデータに分割
train_texts, test_texts, train_labels, test_labels = train_test_split(
    data['Content'].tolist(),
    [0 if 'ネガティブ' in text else 1 for text in data['Content']],  # ラベルの設定例
    test_size=0.2,
    random_state=42
)

# トークナイザーのロード
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-multilingual-cased')

# トークナイズ
train_encodings = tokenizer(train_texts, padding=True, truncation=True, return_tensors='pt')
test_encodings = tokenizer(test_texts, padding=True, truncation=True, return_tensors='pt')

# データセットクラスの定義
class ArticleDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

# 訓練データセットとテストデータセットの作成
train_dataset = ArticleDataset(train_encodings, train_labels)
test_dataset = ArticleDataset(test_encodings, test_labels)

# モデルのロード
model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-multilingual-cased', num_labels=2)

# トレーニング設定（学習率とエポック数を調整）
training_args = TrainingArguments(
    output_dir='./results',
    evaluation_strategy="epoch",
    learning_rate=3e-5,  # 学習率の設定（例: 2e-5）
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=4,  # エポック数の設定（例: 5）
    weight_decay=0.01,
)

# Trainerの作成
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
)

# モデルのトレーニング
trainer.train()

# トレーニング済みモデルを保存
model.save_pretrained('./fine_tuned_bert')
tokenizer.save_pretrained('./fine_tuned_bert')
