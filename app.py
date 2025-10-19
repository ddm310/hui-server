from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import logging
import random
import urllib.parse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def translate_text(text):
    """Перевод через Google Translate"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
    logger.info(f"🧠 Перевод: '{text}'")
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
            logger.info(f"✅ Перевел: '{translation}'")
            return translation
        else:
            logger.warning("⚠️ Google Translate не сработал, используем оригинал")
            return text
    except Exception as e:
        logger.warning(f"⚠️ Ошибка перевода: {e}, используем оригинал")
        return text

def generate_with_pollinations(prompt):
    """Генерация через Pollinations"""
    try:
        # Добавляем случайность для разных результатов
        seed = random.randint(1, 1000000)
        
        # Используем FLUX для лучшего качества
        final_prompt = f"{prompt} --seed {seed} --model flux"
        encoded_prompt = urllib.parse.quote(final_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        
        logger.info(f"🎯 Pollinations запрос: {final_prompt}")
        
        response = requests.get(url, timeout=45)
        
        if response.status_code == 200:
            logger.info("✅ Изображение сгенерировано!")
            return response.content
        else:
            logger.error(f"❌ Ошибка Pollinations: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка Pollinations: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        prompt = request.form.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Введите описание"}), 400

        # Переводим промпт
        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Оригинал: '{prompt}' -> Перевод: '{translated_prompt}'")

        # Генерируем изображение
        result = generate_with_pollinations(translated_prompt)
        
        if result:
            return send_file(io.BytesIO(result), mimetype='image/png')
        else:
            return jsonify({"error": "Сервис генерации временно недоступен"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "OK", 
        "message": "Сервер работает",
        "service": "Pollinations Image Generator"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
