from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from functools import lru_cache

_model_cache = None

def load_sentiment_model():
    global _model_cache
    if _model_cache is None:
        model_name = "cl-tohoku/bert-base-japanese-sentiment"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
        _model_cache = (tokenizer, model)
    return _model_cache

@lru_cache(maxsize=100)
def cached_analyze_sentiment(query):
    tokenizer, model = load_sentiment_model()
    inputs = tokenizer(query, max_length=128, truncation=True, padding="longest", return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        prediction = torch.argmax(outputs.logits, dim=1).item()
    labels = ["否定的", "中立的", "肯定的"]
    return labels[prediction]