from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def generate_image(prompt):
    """Генерация изображения с повторными попытками"""
    # Попробуем несколько моделей
    models = [
        "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5",
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
        "https://api-inference.huggingface.co/models/ogkalu/Stable-Diffusion-v1-5"
    ]
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    for model_url in models:
        try:
            print(f"Пробуем модель: {model_url}")
            
            response = requests.post(model_url, headers=headers, json={
                "inputs": prompt,
                "options": {
                    "wait_for_model": True,
                    "use_cache": True
                },
                "parameters": {
                    "max_new_tokens": 1000
                }
            })
            
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                # Модель загружается, пробуем следующую
                print(f"Модель {model_url} загружается, пробуем следующую...")
                continue
            else:
                print(f"Ошибка от модели {model_url}: {response.text}")
                continue
                
        except Exception as e:
            print(f"Ошибка с моделью {model_url}: {str(e)}")
            continue
    
    # Если все модели не сработали
    raise Exception("Все модели недоступны")

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"Получен промпт: {prompt}")
        
        # Генерация изображения
        image_bytes = generate_image(prompt)
        
        # Возвращаем изображение
        return send_file(
            io.BytesIO(image_bytes),
            mimetype='image/png'
        )
        
    except Exception as e:
        error_msg = f"Ошибка генерации: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

@app.route('/test-model', methods=['GET'])
def test_model():
    """Тестовый endpoint для проверки модели"""
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        test_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
        
        response = requests.post(test_url, headers=headers, json={
            "inputs": "test image",
            "options": {"wait_for_model": False}
        })
        
        return jsonify({
            "status": response.status_code,
            "message": response.text[:200] if response.text else "No response"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
