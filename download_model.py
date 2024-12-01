from transformers import AutoModel, AutoTokenizer

# モデル名
model_name = "distilbert-base-uncased"
# 保存先ディレクトリを指定
save_directory = "./models"

print(f"Downloading model: {model_name}")
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=save_directory)
model = AutoModel.from_pretrained(model_name, cache_dir=save_directory)

print(f"Model downloaded and saved in {save_directory}.")
