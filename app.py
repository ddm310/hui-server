from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random
import logging
import base64

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

PROXY_SERVER_URL = os.getenv('PROXY_SERVER_URL', 'https://gemini-proxy.up.railway.app')

def translate_with_deepseek(text):
    """Перевод через DeepSeek API"""
    logger.info(f"🧠 Перевод: '{text}'")
    try:
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={'Content-Type': 'application/json'},
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'system', 
                        'content': 'You are a professional translator. Translate Russian to English accurately. Return only the translation without any additional text.'
                    },
                    {
                        'role': 'user', 
                        'content': f'Translate this to English: "{text}"'
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 1000
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            translation = result['choices'][0]['message']['content'].strip().strip('"')
            logger.info(f"✅ Перевел: '{translation}'")
            return translation
        else:
            logger.error(f"❌ DeepSeek статус: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка перевода: {e}")
        return None

def translate_text(text):
    """Основная функция перевода"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
    translation = translate_with_deepseek(text)
    return translation if translation else text

def generate_with_gemini_proxy(prompt, image_data=None):
    """Генерация через наш прокси-сервер"""
    try:
        proxy_url = f"{PROXY_SERVER_URL}/generate-image"
        
        payload = {
            'prompt': prompt
        }
        
        # Если есть изображение, добавляем его в base64
        if image_data:
            payload['imageData'] = base64.b64encode(image_data).decode('utf-8')
        
        logger.info(f"🎯 Отправка в прокси: '{prompt}'")
        
        response = requests.post(
            proxy_url,
            json=payload,
            timeout=120
        )
        
        logger.info(f"📡 Статус прокси: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ Прокси генерация успешна!")
            return response.content
        else:
            error_text = response.text[:500] if response.text else "No error details"
            logger.error(f"❌ Ошибка прокси: {error_text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к прокси: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        # Определяем тип запроса
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            prompt = request.form.get('prompt', '')
            model_name = request.form.get('model', 'nanobanano')
            image_file = request.files.get('image')
            edit_mode = request.form.get('edit_mode', 'false').lower() == 'true'
        else:
            data = request.get_json() or {}
            prompt = data.get('prompt', '')
            model_name = data.get('model', 'nanobanano')
            image_file = None
            edit_mode = data.get('edit_mode', False)
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        logger.info(f"🎨 Генерация: '{prompt}'")
        logger.info(f"🔧 Модель: {model_name}")
        
        # Обрабатываем изображение если есть (img2img)
        image_data = None
        if image_file and image_file.filename:
            logger.info("🖼️ Обнаружено изображение для обработки...")
            image_data = image_file.read()
            logger.info(f"📊 Размер изображения: {len(image_data)} bytes")
            
            # Пробуем Gemini прокси
            if PROXY_SERVER_URL:
                logger.info("🚀 Пробуем Gemini прокси...")
                result = generate_with_gemini_proxy(prompt, image_data)
                if result:
                    logger.info("✅ Gemini прокси успешно завершен!")
                    return send_file(io.BytesIO(result), mimetype='image/png')
            
            # Если прокси не сработал
            logger.error("❌ Сервис редактирования изображений недоступен")
            return jsonify({"error": "Сервис редактирования изображений временно недоступен"}), 500
        
        # Обычная генерация (text2img)
        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Если режим редактирования но нет изображения - используем Gemini для текстовой генерации
        if edit_mode and PROXY_SERVER_URL:
            logger.info("🎯 Режим редактирования - пробуем Gemini...")
            result = generate_with_gemini_proxy(translated_prompt)
            if result:
                return send_file(io.BytesIO(result), mimetype='image/png')
        
        # Стандартная генерация через Pollinations
        encoded_prompt = urllib.parse.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
        response = requests.get(url, timeout=60)
        
        logger.info(f"📡 Статус генерации: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ УСПЕХ: Изображение сгенерировано!")
            return send_file(io.BytesIO(response.content), mimetype='image/png')
        else:
            error_msg = response.text[:200] if response.text else "Unknown error"
            logger.error(f"❌ Ошибка генерации: {error_msg}")
            return jsonify({"error": f"Ошибка генерации: {error_msg}"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "OK", 
        "message": "Сервер работает",
        "proxy_url": PROXY_SERVER_URL
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Image Generator API", "status": "active"})

if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    logger.info(f"🔗 Proxy URL: {PROXY_SERVER_URL}")
    app.run(host='0.0.0.0', port=5000, debug=False)
