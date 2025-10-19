from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import logging
import base64
import time

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
            return text
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка перевода: {e}")
        return text

def generate_img2img_hf(prompt, image_data):
    """Настоящий img2img через бесплатные HF API"""
    try:
        # Конвертируем изображение в base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Бесплатные модели которые точно работают
        models = [
            "lllyasviel/sd-controlnet-canny",
            "runwayml/stable-diffusion-v1-5",
            "stabilityai/stable-diffusion-2-1"
        ]
        
        for model in models:
            try:
                logger.info(f"🔧 Пробуем модель: {model}")
                
                # Используем Inference API
                url = f"https://api-inference.huggingface.co/models/{model}"
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "image": image_b64,
                        "strength": 0.7,
                        "guidance_scale": 7.5
                    }
                }
                
                response = requests.post(url, json=payload, timeout=60)
                logger.info(f"📡 Статус {model}: {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"✅ Успех с {model}!")
                    return response.content
                elif response.status_code == 503:
                    logger.info(f"⏳ Модель {model} загружается...")
                    time.sleep(5)  # Ждем и пробуем еще раз
                    response = requests.post(url, json=payload, timeout=60)
                    if response.status_code == 200:
                        return response.content
                
            except Exception as e:
                logger.warning(f"⚠️ Модель {model} не сработала: {e}")
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Ошибка HF img2img: {e}")
        return None

def generate_text2img(prompt):
    """Обычная генерация через Pollinations"""
    try:
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=nanobanano"
        
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.content
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
        logger.info(f"🌐 Перевод: '{translated_prompt}'")

        # Если есть изображение - используем img2img
        if image_file and image_file.filename:
            logger.info("🎨 Режим img2img через Hugging Face")
            image_data = image_file.read()
            
            result = generate_img2img_hf(translated_prompt, image_data)
            if result:
                logger.info("✅ Img2Img успешно завершен!")
                return send_file(io.BytesIO(result), mimetype='image/png')
            else:
                logger.warning("⚠️ Img2img не сработал, пробуем text2img")
                # Fallback на обычную генерацию
                result = generate_text2img(f"{translated_prompt} - based on similar style")
                if result:
                    return send_file(io.BytesIO(result), mimetype='image/png')
        
        # Обычная генерация
        logger.info("🆕 Обычная генерация")
        result = generate_text2img(translated_prompt)
        if result:
            return send_file(io.BytesIO(result), mimetype='image/png')
        else:
            return jsonify({"error": "Ошибка генерации"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
