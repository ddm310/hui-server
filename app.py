from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random

# Сначала создаем приложение
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
                'Content-Type': 'application/json'
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

def describe_image_for_prompt(image_file):
    """Простая функция для описания изображения"""
    if image_file and image_file.filename:
        if 'portrait' in image_file.filename.lower():
            return "a portrait photo"
        elif 'landscape' in image_file.filename.lower():
            return "a landscape photo" 
        elif 'city' in image_file.filename.lower():
            return "an urban cityscape"
        else:
            return "an uploaded image"
    return "an uploaded image"

# ТЕПЕРЬ добавляем роуты после объявления всех функций

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        model_name = data.get('model', 'nanobanano')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"📝 Оригинальный промпт: '{prompt}'")
        
        # Автоматический перевод
        translated_prompt = translate_text(prompt)
        
        print(f"🔧 Модель: {model_name}")
        print(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Генерация изображения
        encoded_prompt = urllib.parse.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        
        if model_name in ["nanobanano", "pollinations", "flux", "dalle", "stable-diffusion", "midjourney"]:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
        else:
            url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        if model_name in ["nanobanano", "pollinations", "flux", "dalle", "stable-diffusion", "midjourney"]:
            response = requests.get(url, timeout=60)
        else:
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}
            response = requests.post(url, headers=headers, json={
                "inputs": translated_prompt,
                "options": {"wait_for_model": True}
            })
        
        print(f"🔹 Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ УСПЕХ: Изображение сгенерировано!")
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            error_msg = response.text[:500] if response.text else "Unknown error"
            print(f"❌ Ошибка API: {error_msg}")
            return jsonify({"error": f"Ошибка модели: {error_msg}"}), 500
        
    except Exception as e:
        error_msg = f"Ошибка генерации: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/generate-smart', methods=['POST'])
def generate_smart():
    """Умная генерация с псевдо-img2img"""
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            prompt = request.form.get('prompt', '')
            model_name = request.form.get('model', 'nanobanano')
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            prompt = data.get('prompt', '') if data else ''
            model_name = data.get('model', 'nanobanano') if data else 'nanobanano'
            image_file = None
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"📝 Промпт: '{prompt}'")
        
        # Если есть изображение, создаем улучшенный промпт
        image_description = ""
        if image_file and image_file.filename:
            image_description = describe_image_for_prompt(image_file)
            print(f"🖼️ Описание изображения: {image_description}")
        
        # Создаем финальный промпт
        if image_description:
            final_prompt = f"{prompt} - based on {image_description} maintaining similar style"
        else:
            final_prompt = prompt
        
        # Перевод промпта
        translated_prompt = translate_text(final_prompt)
        print(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Генерация
        encoded_prompt = urllib.parse.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
        
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            return jsonify({"error": "Ошибка генерации"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

@app.route('/translate', methods=['POST'])
def translate_endpoint():
    """Отдельный endpoint для тестирования перевода"""
    try:
        data = request.get_json()
        text = data.get('text', '') if data else ''
        
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
