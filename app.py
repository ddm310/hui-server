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

def translate_with_deepseek(text):
    """Перевод через DeepSeek API"""
    print("🧠 DeepSeek: Перевод...")
    try:
        # DeepSeek API для перевода (бесплатный)
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.getenv("DEEPSEEK_API_KEY", "free")}'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a professional translator. Translate the following Russian text to English accurately while preserving the meaning and context. Return only the translation without any additional text.'
                    },
                    {
                        'role': 'user', 
                        'content': f'Переведи на английский: "{text}"'
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 1000
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            translation = result['choices'][0]['message']['content'].strip()
            # Убираем кавычки если они есть
            translation = translation.strip('"')
            print(f"✅ DeepSeek перевел: '{translation}'")
            return translation
        else:
            print(f"❌ DeepSeek статус: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ DeepSeek ошибка: {e}")
        return None

def translate_with_google_simple(text):
    """Простой Google Translate через неофициальный API"""
    print("🔍 Google: Перевод...")
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'ru',
            'tl': 'en',
            'dt': 't',
            'q': text
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            translation = result[0][0][0]
            print(f"✅ Google перевел: '{translation}'")
            return translation
        else:
            print(f"❌ Google статус: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Google ошибка: {e}")
        return None

def translate_text(text):
    """Основная функция перевода с приоритетом DeepSeek"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text  # Возвращаем оригинал если нет русских букв
    
    # Пробуем DeepSeek сначала
    translation = translate_with_deepseek(text)
    if translation:
        return translation
    
    # Если DeepSeek не сработал, пробуем Google
    translation = translate_with_google_simple(text)
    if translation:
        return translation
    
    # Если все провалилось, возвращаем оригинал
    print("⚠️ Все переводчики недоступны, используем оригинальный текст")
    return text

def generate_with_pollinations(prompt, model="pollinations"):
    """Генерация через Pollinations.ai"""
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1, 1000000)
    
    models = {
        "pollinations": "pollinations",
        "flux": "flux", 
        "dalle": "dalle"
    }
    
    selected_model = models.get(model, "pollinations")
    
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={selected_model}&width=512&height=512&seed={seed}&nofilter=true"
    
    print(f"🎨 Генерация: {selected_model}, seed: {seed}")
    response = requests.get(pollinations_url, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Pollinations error: {response.status_code}")

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
        model_name = data.get('model', 'pollinations')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"📝 Оригинальный промпт: '{prompt}'")
        
        # Автоматический перевод
        translated_prompt = translate_text(prompt)
        
        print(f"🔧 Модель: {model_name}")
        print(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Генерация изображения
        if model_name in ["pollinations", "flux", "dalle"]:
            image_bytes = generate_with_pollinations(translated_prompt, model_name)
        else:
            image_bytes = generate_with_huggingface(translated_prompt, model_name)
        
        print("✅ УСПЕХ: Изображение сгенерировано!")
        
        # Возвращаем изображение и информацию о переводе
        response_data = {
            "image_data": image_bytes,
            "translation_info": {
                "original": prompt,
                "translated": translated_prompt,
                "was_translated": prompt != translated_prompt
            }
        }
        
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

@app.route('/translate', methods=['POST'])
def translate_endpoint():
    """Отдельный endpoint для тестирования перевода"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "Текст не может быть пустым"}), 400
        
        print(f"🧪 Тест перевода: '{text}'")
        
        # Пробуем все переводчики
        deepseek_result = translate_with_deepseek(text)
        google_result = translate_with_google_simple(text)
        
        return jsonify({
            "original": text,
            "deepseek_translation": deepseek_result,
            "google_translation": google_result,
            "is_russian": any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
