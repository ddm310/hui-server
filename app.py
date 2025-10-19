from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import logging
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# NVIDIA API ключ (бесплатный)
NVIDIA_API_KEY = os.getenv('NVIDIA_API_KEY', 'nvapi-xxx')  # Получи на developer.nvidia.com

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

def generate_with_nvidia(prompt, image_data=None):
    """Генерация через NVIDIA API"""
    try:
        if image_data:
            # Режим img2img
            url = "https://integrate.api.nvidia.com/v1/editing/nv-ai-foundation/playground_flux"
            payload = {
                "prompt": prompt,
                "image": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}",
                "strength": 0.7,
                "steps": 20
            }
        else:
            # Режим text2img
            url = "https://integrate.api.nvidia.com/v1/generation/nv-ai-foundation/sd_xl_turbo"
            payload = {
                "prompt": prompt,
                "steps": 4,
                "width": 512,
                "height": 512
            }
        
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            # NVIDIA возвращает base64 изображение
            image_b64 = result['data'][0]['image']
            return base64.b64decode(image_b64)
        else:
            logger.error(f"❌ NVIDIA ошибка: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка NVIDIA: {e}")
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

        image_data = None
        if image_file and image_file.filename:
            image_data = image_file.read()
            logger.info("🎨 Режим img2img через NVIDIA")
        else:
            logger.info("🆕 Режим text2img через NVIDIA")
        
        result = generate_with_nvidia(translated_prompt, image_data)
        
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
