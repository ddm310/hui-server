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

PROXY_SERVER_URL = os.getenv('PROXY_SERVER_URL')

def generate_with_gemini_proxy(prompt, image_data=None):
    """Только Gemini через прокси"""
    try:
        proxy_url = f"{PROXY_SERVER_URL}/generate-image"
        
        payload = {'prompt': prompt}
        
        if image_data:
            payload['imageData'] = base64.b64encode(image_data).decode('utf-8')
        
        logger.info(f"🎯 Отправка в Gemini: '{prompt}'")
        
        response = requests.post(proxy_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            logger.info("✅ Gemini успешно!")
            return response.content
        else:
            logger.error(f"❌ Ошибка Gemini: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка подключения: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        prompt = request.form.get('prompt', '')
        image_file = request.files.get('image')
        
        if not prompt:
            return jsonify({"error": "Введите описание"}), 400
        
        image_data = None
        if image_file and image_file.filename:
            image_data = image_file.read()
        
        result = generate_with_gemini_proxy(prompt, image_data)
        
        if result:
            return send_file(io.BytesIO(result), mimetype='image/png')
        else:
            return jsonify({"error": "Gemini временно недоступен"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "proxy_url": PROXY_SERVER_URL})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
