from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import logging
import random
import urllib.parse
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

def translate_text(text):
    """Простой перевод"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {'client': 'gtx', 'sl': 'ru', 'tl': 'en', 'dt': 't', 'q': text}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()[0][0][0]
        return text
    except:
        return text

def analyze_image_for_prompt(image_data, original_prompt):
    """Анализируем изображение чтобы создать умный промпт"""
    try:
        # Открываем изображение для анализа
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        
        # Определяем ориентацию
        if width > height:
            orientation = "landscape"
            ratio = "wide"
        elif height > width:
            orientation = "portrait" 
            ratio = "tall"
        else:
            orientation = "square"
            ratio = "square"
        
        # Определяем примерный тип изображения по размерам
        if width >= 1000 or height >= 1000:
            image_type = "high resolution"
        else:
            image_type = "standard"
        
        # Создаём умный промпт
        smart_prompt = f"{original_prompt} - {orientation} {ratio} composition, {image_type} quality, maintaining original style and colors --style realistic --seed {random.randint(1, 1000000)}"
        
        logger.info(f"💡 Умный промпт: {smart_prompt}")
        return smart_prompt
        
    except Exception as e:
        logger.warning(f"⚠️ Не удалось проанализировать изображение: {e}")
        return f"{original_prompt} --style realistic --seed {random.randint(1, 1000000)}"

def generate_with_pollinations(prompt):
    """Генерация через Pollinations"""
    try:
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        
        logger.info(f"🌐 Запрос к Pollinations: {url[:100]}...")
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"❌ Pollinations ошибка: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка Pollinations: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        prompt = request.form.get('prompt', '')
        image_file = request.files.get('image')
        
        if not prompt:
            return jsonify({"error": "Введите описание"}), 400

        translated_prompt = translate_text(prompt)
        logger.info(f"🎯 Оригинал: '{prompt}'")
        logger.info(f"🎯 Перевод: '{translated_prompt}'")

        # Если есть изображение - создаём умный промпт
        if image_file and image_file.filename:
            logger.info("🎨 Режим псевдо-img2img через умные промпты")
            image_data = image_file.read()
            
            # Создаём умный промпт на основе изображения
            smart_prompt = analyze_image_for_prompt(image_data, translated_prompt)
            result = generate_with_pollinations(smart_prompt)
            
            if result:
                logger.info("✅ Псевдо-img2img успешно!")
                return send_file(io.BytesIO(result), mimetype='image/png')
        
        # Обычная генерация
        logger.info("🆕 Обычная генерация")
        final_prompt = f"{translated_prompt} --style realistic --seed {random.randint(1, 1000000)}"
        result = generate_with_pollinations(final_prompt)
        
        if result:
            logger.info("✅ Генерация успешна!")
            return send_file(io.BytesIO(result), mimetype='image/png')
        else:
            return jsonify({"error": "Сервис временно недоступен. Попробуйте позже."}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": "Ошибка сервера"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
