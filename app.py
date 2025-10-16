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

def translate_text(text):
    """Простой переводчик"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
    # Простой словарь для основных слов
    translations = {
        'красивый': 'beautiful',
        'закат': 'sunset', 
        'над': 'over',
        'морем': 'sea',
        'море': 'sea',
        'небо': 'sky',
        'горы': 'mountains',
        'лес': 'forest',
        'город': 'city',
        'улица': 'street',
        'дом': 'house',
        'кошка': 'cat',
        'собака': 'dog',
        'цветок': 'flower'
    }
    
    # Простая замена слов
    translated = text
    for ru, en in translations.items():
        translated = translated.replace(ru, en)
    
    logger.info(f"🌐 Перевод: '{text}' -> '{translated}'")
    return translated

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            prompt = request.form.get('prompt', '')
            model_name = request.form.get('model', 'nanobanano')
            image_file = request.files.get('image')
        else:
            data = request.get_json() or {}
            prompt = data.get('prompt', '')
            model_name = data.get('model', 'nanobanano')
            image_file = None
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        logger.info(f"🎨 Генерация: '{prompt}'")
        logger.info(f"🔧 Модель: {model_name}")
        
        # Если есть изображение - сообщаем что img2img временно недоступен
        if image_file and image_file.filename:
            logger.info("🖼️ Обнаружено изображение")
            return jsonify({"error": "Редактирование изображений временно недоступно. Используйте режим 'Создать новое'."}), 400
        
        # Обычная генерация (text2img)
        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Стандартная генерация через Pollinations
        encoded_prompt = urllib.parse.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
        
        logger.info(f"📡 Запрос к: {url}")
        response = requests.get(url, timeout=30)
        
        logger.info(f"📡 Статус генерации: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ УСПЕХ: Изображение сгенерировано!")
            return send_file(io.BytesIO(response.content), mimetype='image/png')
        else:
            error_msg = response.text[:200] if response.text else "Unknown error"
            logger.error(f"❌ Ошибка генерации: {error_msg}")
            return jsonify({"error": f"Ошибка генерации. Попробуйте другой промпт."}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Image Generator API", "status": "active"})

if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    app.run(host='0.0.0.0', port=5000, debug=False)
