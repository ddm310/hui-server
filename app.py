from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import logging
import base64
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# NVIDIA API ключ
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY')

def translate_text(text):
    """Простой перевод"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
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
            return result[0][0][0]
        return text
    except:
        return text

def generate_with_nvidia_img2img(prompt, image_data):
    """Img2img через FLUX Kontext"""
    try:
        invoke_url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-kontext-dev"
        
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Accept": "application/json",
        }

        payload = {
            "prompt": prompt,
            "image": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}",
            "aspect_ratio": "match_input_image",
            "steps": 20,
            "cfg_scale": 3.5,
            "seed": random.randint(0, 1000000)
        }

        response = requests.post(invoke_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            # NVIDIA возвращает base64 изображение
            image_b64 = result['data'][0]['image']
            return base64.b64decode(image_b64)
        else:
            logger.error(f"❌ NVIDIA img2img ошибка: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка NVIDIA img2img: {e}")
        return None

def generate_with_nvidia_text2img(prompt):
    """Text2img через FLUX"""
    try:
        invoke_url = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev"
        
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Accept": "application/json",
        }

        payload = {
            "prompt": prompt,
            "mode": "base",
            "cfg_scale": 3.5,
            "width": 512,
            "height": 512,
            "seed": random.randint(0, 1000000),
            "steps": 20
        }

        response = requests.post(invoke_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            image_b64 = result['data'][0]['image']
            return base64.b64decode(image_b64)
        else:
            logger.error(f"❌ NVIDIA text2img ошибка: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка NVIDIA text2img: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        prompt = request.form.get('prompt', '')
        image_file = request.files.get('image')
        
        if not prompt:
            return jsonify({"error": "Введите описание"}), 400

        translated_prompt = translate_text(prompt)
        logger.info(f"🎯 Промпт: '{translated_prompt}'")

        # Если есть изображение - используем img2img
        if image_file and image_file.filename:
            logger.info("🎨 Режим img2img через NVIDIA FLUX Kontext")
            image_data = image_file.read()
            
            result = generate_with_nvidia_img2img(translated_prompt, image_data)
            if result:
                logger.info("✅ NVIDIA img2img успешно!")
                return send_file(io.BytesIO(result), mimetype='image/png')
            else:
                logger.warning("⚠️ NVIDIA img2img не сработал, пробуем text2img")
                result = generate_with_nvidia_text2img(f"{translated_prompt} - editing original image")
        
        # Обычная генерация
        else:
            logger.info("🆕 Режим text2img через NVIDIA FLUX")
            result = generate_with_nvidia_text2img(translated_prompt)
        
        if result:
            logger.info("✅ NVIDIA генерация успешна!")
            return send_file(io.BytesIO(result), mimetype='image/png')
        else:
            return jsonify({"error": "NVIDIA сервис временно недоступен"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": "Ошибка сервера"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
