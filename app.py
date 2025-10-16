from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random
import logging
import base64
import time

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')
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
        logger.info(f"🔗 URL прокси: {proxy_url}")
        
        response = requests.post(
            proxy_url,
            json=payload,
            timeout=120  # Увеличиваем таймаут для генерации
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

def generate_with_hf_img2img(prompt, image_data, strength=0.7):
    """Настоящий img2img через Hugging Face"""
    try:
        logger.info("🎨 Используем Hugging Face img2img...")
        
        # Конвертируем изображение в base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Пробуем разные модели которые поддерживают img2img
        models = [
            "runwayml/stable-diffusion-v1-5",
            "stabilityai/stable-diffusion-2-1",
        ]
        
        for model in models:
            logger.info(f"🔧 Пробуем модель: {model}")
            
            url = f"https://api-inference.huggingface.co/models/{model}"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
            
            payload = {
                "inputs": f"{prompt}",
                "parameters": {
                    "image": image_b64,
                    "strength": strength,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 20
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.info(f"📡 Статус {model}: {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"✅ Успех с моделью {model}!")
                return response.content
            elif response.status_code == 503:
                logger.info(f"⏳ Модель {model} загружается...")
                continue
            else:
                logger.warning(f"⚠️ Модель {model} не сработала: {response.text[:100]}")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка HF img2img: {e}")
        return None

def generate_fallback_img2img(prompt, image_data):
    """Fallback - умный промпт на основе изображения"""
    try:
        logger.info("🔄 Используем fallback (умный промпт)...")
        
        # Анализируем изображение через простые признаки
        from PIL import Image
        import io
        
        img = Image.open(io.BytesIO(image_data))
        
        # Простой анализ цветов
        colors = img.getcolors(maxcolors=256)
        if colors:
            dominant_color = max(colors, key=lambda x: x[0])[1]
            color_desc = f" with dominant {('red', 'green', 'blue', 'yellow', 'purple', 'orange')[dominant_color[0] % 6]} tones"
        else:
            color_desc = ""
        
        # Анализ размера и пропорций
        width, height = img.size
        if width > height:
            orientation = "landscape"
        elif height > width:
            orientation = "portrait" 
        else:
            orientation = "square"
        
        # Создаем улучшенный промпт
        enhanced_prompt = f"{prompt} - editing the uploaded {orientation} image{color_desc} while preserving original composition"
        
        logger.info(f"💡 Умный промпт: '{enhanced_prompt}'")
        
        # Генерация через Pollinations
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=nanobanano&width={width}&height={height}"
        
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.content
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка fallback: {e}")
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
        logger.info(f"📝 Режим редактирования: {edit_mode}")
        
        # Обрабатываем изображение если есть
        image_data = None
        if image_file and image_file.filename:
            logger.info("🖼️ Обнаружено изображение для обработки...")
            image_data = image_file.read()
            logger.info(f"📊 Размер изображения: {len(image_data)} bytes")
            
            # Сначала пробуем Gemini прокси (приоритет)
            if PROXY_SERVER_URL:
                logger.info("🚀 Пробуем Gemini прокси...")
                result = generate_with_gemini_proxy(prompt, image_data)
                if result:
                    logger.info("✅ Gemini прокси успешно завершен!")
                    return send_file(io.BytesIO(result), mimetype='image/png')
                else:
                    logger.warning("⚠️ Gemini прокси не сработал")
            
            # Fallback на другие методы
            logger.info("🔄 Переходим к fallback методам...")
            result = generate_with_hf_img2img(prompt, image_data)
            if not result:
                result = generate_fallback_img2img(prompt, image_data)
            
            if result:
                logger.info("✅ Img2Img успешно завершен через fallback!")
                return send_file(io.BytesIO(result), mimetype='image/png')
            else:
                logger.warning("⚠️ Все методы img2img не сработали")
                return jsonify({"error": "Не удалось обработать изображение"}), 500
        
        # Обычная генерация (text2img)
        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Если включен режим редактирования но нет изображения - используем Gemini
        if edit_mode and PROXY_SERVER_URL:
            logger.info("🎯 Режим редактирования - пробуем Gemini...")
            result = generate_with_gemini_proxy(translated_prompt)
            if result:
                return send_file(io.BytesIO(result), mimetype='image/png')
        
        # Стандартная генерация через Pollinations
        encoded_prompt = urllib.parse.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        
        if model_name in ["nanobanano", "pollinations", "flux", "dalle", "stable-diffusion", "midjourney"]:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
            response = requests.get(url, timeout=60)
        else:
            url = f"https://api-inference.huggingface.co/models/{model_name}"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
            response = requests.post(url, headers=headers, json={
                "inputs": translated_prompt,
                "options": {"wait_for_model": True}
            }, timeout=60)
        
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

if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    logger.info(f"🔗 Proxy URL: {PROXY_SERVER_URL}")
    app.run(host='0.0.0.0', port=5000, debug=False)
