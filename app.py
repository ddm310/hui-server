from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os

app = Flask(__name__)
CORS(app)

# Простая проверка ключа
HF_API_KEY = os.getenv('HF_API_KEY')
if not HF_API_KEY:
    print("⚠️  ВНИМАНИЕ: HF_API_KEY не установлен!")

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        if not HF_API_KEY:
            return jsonify({"error": "API ключ не настроен на сервере"}), 500
        
        # Простая стабильная модель
        API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        
        print(f"Отправляем запрос к API с промптом: {prompt}")
        
        response = requests.post(API_URL, headers=headers, json={
            "inputs": prompt
        })
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            return jsonify({"error": f"Ошибка API ({response.status_code}): {response.text}"}), 500
        
    except Exception as e:
        print(f"Исключение: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
