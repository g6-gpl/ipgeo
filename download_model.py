from huggingface_hub import snapshot_download
from transformers import AutoTokenizer, AutoModel

import os

def download_model_hub(model_id, local_dir):
    """Скачать модель используя huggingface_hub"""
    
    print(f"📥 Скачивание: {model_id}")
    
    # Скачать всю модель
    snapshot_download(
        repo_id=model_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
        allow_patterns=["*.json", "*.model", "*.bin", "*.txt", "config.json"]
    )
    
    print(f"✅ Модель скачана в: {local_dir}")

# Использование
# download_model_hub(
#     "microsoft/deberta-v3-base",
#     "./models/deberta-v3-base-full"
# )

def test_local_model(model_path):
    """Проверить что локальная модель работает"""
    
    try:
        print(f"🧪 Тестируем модель: {model_path}")
        
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModel.from_pretrained(model_path)
        
        # Тестовый текст
        text = "Test input for model verification"
        inputs = tokenizer(text, return_tensors="pt")
        
        outputs = model(**inputs)
        print(f"✅ Модель работает! Output shape: {outputs.last_hidden_state.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

# Проверить скачанную модель
test_local_model("./models/deberta-v3-base-full")