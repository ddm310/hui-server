from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

@app.before_request
def log_request_info():
    """Логируем все входящие запросы"""
    logger.info(f"📥 Входящий запрос: {request.method} {request.path}")
    if request.method == 'POST':
        logger.info(f"   Content-Type: {request.content_type}")
        if request.content_type and 'application/json' in request.content_type:
            logger.info(f"   JSON данные: {request.get_json()}")
        elif request.content_type and 'multipart' in request.content_type:
            logger.info(f"   Form данные: {request.form}")

def translate_with_deepseek(text):
    """Перевод через DeepSeek API"""
    logger.info("🧠 DeepSeek: Перевод...")
    try:
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={'Content-Type': 'application/json'},
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'system', 
                        'content': 'Translate Russian to English accurately. Return only translation.'
                    },
                    {'role': 'user', 'content': f'Переведи: "{text}"'}
                ],
                'temperature': 0.1,
                'max_tokens': 1000
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            translation = result['choices'][0]['message']['content'].strip('"')
            logger.info(f"✅ DeepSeek перевел: '{translation}'")
            return translation
        else:
            logger.error(f"❌ DeepSeek статус: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ DeepSeek ошибка: {e}")
        return None

def translate_text(text):
    """Основная функция перевода"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
    translation = translate_with_deepseek(text)
    return translation if translation else text

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Нет данных в запросе"}), 400
            
        prompt = data.get('prompt', '')
        model_name = data.get('model', 'nanobanano')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        logger.info(f"🎨 Начинаем генерацию: '{prompt}'")
        logger.info(f"🔧 Модель: {model_name}")
        
        # Автоматический перевод
        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Генерация изображения
        encoded_prompt = urllib.parse.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        
        if model_name in ["nanobanano", "pollinations", "flux", "dalle", "stable-diffusion", "midjourney"]:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
            logger.info(f"🔗 Pollinations URL: {url}")
            response = requests.get(url, timeout=60)
        else:
            url = f"https://api-inference.huggingface.co/models/{model_name}"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
            logger.info(f"🔗 Hugging Face URL: {url}")
            response = requests.post(url, headers=headers, json={
                "inputs": translated_prompt,
                "options": {"wait_for_model": True}
            }, timeout=60)
        
        logger.info(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ УСПЕХ: Изображение сгенерировано!")
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            error_msg = response.text[:200] if response.text else "Unknown error"
            logger.error(f"❌ Ошибка API: {error_msg}")
            return jsonify({"error": f"Ошибка генерации: {error_msg}"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    logger.info("🔍 Проверка здоровья сервера")
    return jsonify({"status": "OK", "message": "Сервер работает"})

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Тестовый endpoint"""
    logger.info("🧪 Тестовый запрос")
    return jsonify({
        "message": "Сервер работает!", 
        "timestamp": random.randint(1, 1000)
    })

if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    app.run(host='0.0.0.0', port=5000, debug=False)
