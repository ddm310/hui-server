from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random
import json
import base64
from PIL import Image

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def translate_with_deepseek(text):
    """Перевод через DeepSeek API"""
    print("🧠 DeepSeek: Перевод...")
    try:
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
            translation = translation.strip('"')
            print(f"✅ DeepSeek перевел: '{translation}'")
            return translation
        else:
            print(f"❌ DeepSeek статус: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ DeepSeek ошибка: {e}")
        return None

def translate_text(text):
    """Основная функция перевода"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
    translation = translate_with_deepseek(text)
    if translation:
        return translation
    
    print("⚠️ Переводчик недоступен, используем оригинальный текст")
    return text

def generate_with_pollinations(prompt, model="nanobanano", image_data=None):
    """Генерация через Pollinations.ai с поддержкой изображений"""
    encoded_prompt = urllib.parse.quote(prompt)
    seed = random.randint(1, 1000000)
    
    models = {
        "nanobanano": "nanobanano",
        "pollinations": "pollinations",
        "flux": "flux", 
        "dalle": "dalle",
        "stable-diffusion": "stable-diffusion",
        "midjourney": "midjourney"
    }
    
    selected_model = models.get(model, "nanobanano")
    
    # Базовый URL
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={selected_model}&width=512&height=512&seed={seed}&nofilter=true"
    
    # Если есть изображение, добавляем параметр для img2img
    if image_data and model == "nanobanano":
        # Конвертируем изображение в base64 и добавляем к URL
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            pollinations_url += f"&image={image_b64}"
        print("🖼️ Используем режим img2img с загруженным изображением")
    
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

def process_uploaded_image(image_file):
    """Обработка загруженного изображения"""
    try:
        # Читаем файл
        image_data = image_file.read()
        
        # Проверяем и конвертируем изображение
        img = Image.open(io.BytesIO(image_data))
        
        # Ресайз если нужно (опционально)
        if img.size[0] > 1024 or img.size[1] > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        
        # Конвертируем обратно в bytes
        output = io.BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
        
    except Exception as e:
        raise Exception(f"Ошибка обработки изображения: {str(e)}")

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        # Проверяем Content-Type
        if request.content_type.startswith('multipart/form-data'):
            # Форма с файлом
            prompt = request.form.get('prompt', '')
            model_name = request.form.get('model', 'nanobanano')
            image_file = request.files.get('image')
        else:
            # JSON запрос (без изображения)
            data = request.json
            prompt = data.get('prompt', '')
            model_name = data.get('model', 'nanobanano')
            image_file = None
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"📝 Оригинальный промпт: '{prompt}'")
        
        # Автоматический перевод
        translated_prompt = translate_text(prompt)
        
        print(f"🔧 Модель: {model_name}")
        print(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Обрабатываем изображение если есть
        image_data = None
        if image_file and image_file.filename:
            print("🖼️ Обрабатываем загруженное изображение...")
            image_data = process_uploaded_image(image_file)
            print("✅ Изображение обработано")
        
        # Генерация изображения
        if model_name in ["nanobanano", "pollinations", "flux", "dalle", "stable-diffusion", "midjourney"]:
            image_bytes = generate_with_pollinations(translated_prompt, model_name, image_data)
        else:
            image_bytes = generate_with_huggingface(translated_prompt, model_name)
        
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

@app.route('/translate', methods=['POST'])
def translate_endpoint():
    """Отдельный endpoint для тестирования перевода"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "Текст не может быть пустым"}), 400
        
        print(f"🧪 Тест перевода: '{text}'")
        
        deepseek_result = translate_with_deepseek(text)
        
        return jsonify({
            "original": text,
            "deepseek_translation": deepseek_result,
            "is_russian": any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
