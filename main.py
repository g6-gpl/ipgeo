from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import csv

model_name = "./models/deberta-v3-base-full"

try:

    tokenizer = AutoTokenizer.from_pretrained(model_name)

    model = AutoModelForSequenceClassification.from_pretrained(model_name)

    print("✅ Модель и токенизатор успешно загружены!")

except Exception as e:
    print(f"❌ Ошибка загрузки модели: {e}")
    exit(1)


classifier = pipeline(
    "text-classification",
    model=model,
    tokenizer=tokenizer,
    framework="pt",
    device=0 if torch.cuda.is_available() else -1,
)


def analyze_network_traffic(traffic_data):
    text_features = []
    for packet in traffic_data:
        feature_str = (
            f"SRC:{packet['src_ip']} DST:{packet['dst_ip']} "
            f"PORT:{packet['dst_port']} PROTO:{packet['protocol']} "
            f"SIZE:{packet['length']} FLAGS:{packet.get('flags', 'None')}"
        )
        text_features.append(feature_str)

    try:
        results = classifier(text_features)
    except:

        results = []
        for text in text_features:
            try:
                result = classifier(text)
                results.extend(result)
            except Exception as e:
                print(f"❌ Ошибка при обработке текста: {text[:50]}... - {e}")
                results.append({"label": "ERROR", "score": 0.0})

    return results

with open(r'files\01.csv', 'r', newline='') as csvfile:
    reader = csv.reader(csvfile)
    header = next(reader)
    data = []
    for row in reader:
        data.append(row)
        

sample_traffic = list(str(data))


try:
    analysis = analyze_network_traffic(sample_traffic)
    print("📊 Результаты анализа трафика:")
    for i, result in enumerate(analysis):
        print(f"Пакет {i+1}: {result}")
except Exception as e:
    print(f"❌ Ошибка при анализе трафика: {e}")
