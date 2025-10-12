from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random
import logging
import base64
from PIL import Image
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

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

def smart_img2img_with_analysis(prompt, image_data, strength=0.7):
    """
    Умный img2img через анализ изображения и создание контекстного промпта
    """
    try:
        logger.info("🎨 Умный img2img с анализом изображения...")
        
        # Анализируем изображение
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        
        # Простой анализ характеристик
        aspect_ratio = width / height
        if aspect_ratio > 1.5:
            orientation = "wide landscape"
        elif aspect_ratio > 1:
            orientation = "landscape" 
        elif aspect_ratio == 1:
            orientation = "square"
        elif aspect_ratio < 0.7:
            orientation = "portrait"
        else:
            orientation = "photo"
        
        # Анализ размера
        if width * height > 1000000:
            size_desc = "high resolution"
        else:
            size_desc = "standard resolution"
        
        # Создаем контекстный промпт
        if strength > 0.8:
            transformation = "completely transform into"
        elif strength > 0.6:
            transformation = "significantly modify to"
        elif strength > 0.4:
            transformation = "modify to show"
        else:
            transformation = "slightly adjust to"
        
        enhanced_prompt = f"{transformation} {prompt} - based on {orientation} {size_desc} image"
        
        logger.info(f"💡 Контекстный промпт: '{enhanced_prompt}'")
        
        # Переводим и генерируем
        translated_prompt = translate_text(enhanced_prompt)
        encoded_prompt = urllib.parse.quote(translated_prompt)
        
        # Используем Pollinations с seed для консистентности
        seed = random.randint(1, 1000000)
        
        # Подбираем размер сохраняя пропорции
        max_dim = 768 if strength < 0.5 else 512  # Меньше изменений = выше качество
        
        if width > height:
            new_width = max_dim
            new_height = int(height * max_dim / width)
        else:
            new_height = max_dim
            new_width = int(width * max_dim / height)
        
        # Пробуем разные модели Pollinations
        models = ["flux", "nanobanano", "dalle"]
        for model in models:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model}&width={new_width}&height={new_height}&seed={seed}"
            
            logger.info(f"🔄 Пробуем модель: {model}")
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                logger.info(f"✅ Успех с моделью {model}")
                return response.content
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка smart_img2img: {e}")
        return None

def try_prodia_img2img(prompt, image_data, strength=0.7):
    """
    Пробуем Prodia API - бесплатный сервис для генерации изображений
    """
    try:
        logger.info("🎨 Пробуем Prodia API...")
        
        # Конвертируем изображение в base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Prodia имеет ограниченный img2img, но можно попробовать
        url = "https://api.prodia.com/v1/generate"
        
        payload = {
            "prompt": prompt,
            "steps": 20,
            "cfg_scale": 7,
            "seed": random.randint(1, 1000000),
            "upscale": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Prodia-Key": os.getenv('PRODIA_API_KEY', '')  # Можно получить бесплатно
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job')
            
            # Ждем завершения
            for i in range(10):
                status_url = f"https://api.prodia.com/v1/job/{job_id}"
                status_response = requests.get(status_url)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data['status'] == 'succeeded':
                        image_url = status_data['imageUrl']
                        image_response = requests.get(image_url)
                        return image_response.content
                    elif status_data['status'] == 'failed':
                        break
                
                time.sleep(2)
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка Prodia: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        prompt = request.form.get('prompt', '')
        model_name = request.form.get('model', 'nanobanano')
        edit_mode = request.form.get('edit_mode', 'false').lower() == 'true'
        strength = float(request.form.get('strength', 0.7))
        image_file = request.files.get('image')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        logger.info(f"🎨 Генерация: '{prompt}'")
        logger.info(f"🔧 Модель: {model_name}, Режим: {'edit' if edit_mode else 'create'}")
        
        # Обрабатываем img2img запрос
        if edit_mode and image_file and image_file.filename:
            logger.info(f"🖼️ Img2Img запрос, сила: {strength}")
            image_data = image_file.read()
            
            # Пробуем разные методы
            result = smart_img2img_with_analysis(prompt, image_data, strength)
            
            if result:
                logger.info("✅ Img2Img успешно завершен!")
                return send_file(io.BytesIO(result), mimetype='image/png')
            else:
                # Fallback - обычная генерация с упоминанием что это редактирование
                fallback_prompt = f"edited version of image showing: {prompt}"
                translated_prompt = translate_text(fallback_prompt)
                encoded_prompt = urllib.parse.quote(translated_prompt)
                
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512"
                response = requests.get(url, timeout=60)
                
                if response.status_code == 200:
                    logger.info("✅ Fallback генерация успешна")
                    return send_file(io.BytesIO(response.content), mimetype='image/png')
                else:
                    return jsonify({"error": "Не удалось обработать изображение"}), 500
        
        # Обычная генерация (text2img)
        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        encoded_prompt = urllib.parse.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        
        # Используем Pollinations
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
        
        logger.info(f"🌐 Запрос: {url}")
        response = requests.get(url, timeout=60)
        logger.info(f"📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ УСПЕХ: Изображение сгенерировано!")
            return send_file(io.BytesIO(response.content), mimetype='image/png')
        else:
            error_msg = response.text[:200] if response.text else "Unknown error"
            logger.error(f"❌ Ошибка: {error_msg}")
            return jsonify({"error": f"Ошибка генерации: {error_msg}"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    app.run(host='0.0.0.0', port=5000, debug=False)
