from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        # Генерация через Hugging Face - ИСПРАВЛЕННАЯ МОДЕЛЬ
        API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        
        response = requests.post(API_URL, headers=headers, json={
            "inputs": prompt,
            "options": {
                "wait_for_model": True,
                "use_cache": True
            }
        })
        
        if response.status_code != 200:
            return jsonify({"error": f"Ошибка API: {response.text}"}), 500
        
        # Возвращаем изображение напрямую
        return send_file(
            io.BytesIO(response.content),
            mimetype='image/png'
        )
        
    except Exception as e:
        return jsonify({"error": f"Ошибка генерации: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
