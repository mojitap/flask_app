from transformers import DistilBertForSequenceClassification

# モデルのロード
model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased')

print("モデルが正常にロードされました。")
