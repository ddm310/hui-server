from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Разрешаем запросы с вашего сайта

# Получаем API ключ из переменных окружения
HF_API_KEY = os.getenv('HF_API_KEY')

def generate_image(prompt):
    """Генерация изображения через Hugging Face"""
    API_URL = "https://api-inference.huggingface.co/models/ai-forever/ruStableDiffusion"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    response = requests.post(API_URL, headers=headers, json={
        "inputs": prompt,
        "options": {
            "wait_for_model": True,
            "use_cache": True
        }
    })
    
    if response.status_code != 200:
        raise Exception(f"Ошибка API: {response.text}")
    
    return response.content

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"Генерируем изображение для промпта: {prompt}")
        
        # Генерируем изображение
        image_bytes = generate_image(prompt)
        
        # Возвращаем изображение
        return send_file(
            io.BytesIO(image_bytes),
            mimetype='image/png',
            as_attachment=False  # Показываем в браузере, не скачиваем
        )
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return jsonify({"error": f"Ошибка генерации: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
