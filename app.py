from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random
import json

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def generate_with_pollinations(prompt, model="nanobanano"):
    """Генерация через Pollinations.ai с случайным seed"""
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Добавляем случайный seed для разных результатов
    seed = random.randint(1, 1000000)
    
    models = {
        "nanobanano": "nanobanano",
        "pollinations": "pollinations", 
        "flux": "flux",
        "dalle": "dalle"
    }
    
    selected_model = models.get(model, "nanobanano")
    
    # Pollinations URL с seed и параметрами
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={selected_model}&width=512&height=512&seed={seed}&nofilter=true"
    
    print(f"🔧 Используем модель: {selected_model}, seed: {seed}")
    response = requests.get(pollinations_url, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Pollinations error: {response.status_code}")

def generate_with_nanobanano_direct(prompt):
    """Прямое обращение к NanoBanano API с поддержкой русского"""
    try:
        # Пробуем разные варианты NanoBanano API
        seed = random.randint(1, 1000000)
        
        # Вариант 1: Через их официальный API если есть
        nanobanano_url = "https://api.nanobanano.com/generate"
        
        payload = {
            "prompt": prompt,
            "model": "flux",
            "width": 512,
            "height": 512,
            "steps": 20,
            "seed": seed,
            "enhance_prompt": True  # Важно для русского!
        }
        
        response = requests.post(
            nanobanano_url, 
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'image' in result:
                import base64
                image_data = result['image']
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                return base64.b64decode(image_data)
        
        # Если не сработало, используем Pollinations с улучшенными параметрами
        return generate_with_pollinations_enhanced(prompt, "nanobanano")
        
    except Exception as e:
        raise Exception(f"NanoBanano error: {str(e)}")

def generate_with_pollinations_enhanced(prompt, model="nanobanano"):
    """Улучшенная версия для русского текста"""
    # Правильно кодируем русский текст
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1, 1000000)
    
    # Добавляем параметры для лучшего понимания русского
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model}&width=512&height=512&seed={seed}&enhance=true"
    
    print(f"🔧 Улучшенная генерация для русского: {prompt}")
    response = requests.get(pollinations_url, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Pollinations enhanced error: {response.status_code}")

def generate_with_huggingface(prompt, model_name):
    """Генерация через Hugging Face"""
    model_url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    response = requests.post(model_url, headers=headers, json={
        "inputs": prompt,
        "options": {"wait_for_model": True}
    })
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"HF error: {response.status_code} - {response.text}")

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        model_name = data.get('model', 'nanobanano')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"🎨 Генерируем: {prompt}")
        print(f"🔧 Модель: {model_name}")
        
        # Для NanoBanano используем улучшенную версию с поддержкой русского
        if model_name == "nanobanano":
            image_bytes = generate_with_nanobanano_direct(prompt)
        elif model_name in ["pollinations", "flux", "dalle"]:
            image_bytes = generate_with_pollinations_enhanced(prompt, model_name)
        else:
            image_bytes = generate_with_huggingface(prompt, model_name)
        
        print("✅ УСПЕХ: Изображение сгенерировано!")
        return send_file(
            io.BytesIO(image_bytes),
            mimetype='image/png'
        )
        
    except Exception as e:
        error_msg = f"Ошибка генерации: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
