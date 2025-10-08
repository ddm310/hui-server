from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import time
import random

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"Генерируем изображение для: {prompt}")
        
        # Бесплатный API от Prodia (работает без ключа)
        API_URL = "https://api.prodia.com/v1/sd/generate"
        
        # Создаем задание на генерацию
        response = requests.post(API_URL, json={
            "prompt": prompt,
            "model": "dreamshaper_8.safetensors [9d40847d]",
            "steps": 25,
            "cfg_scale": 7,
            "seed": random.randint(1, 1000000),
            "upscale": False
        })
        
        print(f"Статус создания задания: {response.status_code}")
        
        if response.status_code == 200:
            job_id = response.json().get('job')
            print(f"Job ID: {job_id}")
            
            # Ждем завершения генерации (макс 30 секунд)
            for i in range(30):
                result_response = requests.get(f"https://api.prodia.com/v1/job/{job_id}")
                result_data = result_response.json()
                status = result_data.get('status')
                
                print(f"Проверка {i+1}/30: {status}")
                
                if status == 'succeeded':
                    image_url = result_data.get('imageUrl')
                    print(f"Изображение готово: {image_url}")
                    
                    # Скачиваем изображение
                    image_response = requests.get(image_url)
                    return send_file(
                        io.BytesIO(image_response.content),
                        mimetype='image/jpeg'
                    )
                elif status == 'failed':
                    return jsonify({"error": "Генерация не удалась"}), 500
                    
                time.sleep(1)  # Ждем 1 секунду между проверками
            
            return jsonify({"error": "Генерация заняла слишком много времени"}), 500
            
        else:
            error_text = response.text
            print(f"Ошибка API: {error_text}")
            return jsonify({"error": f"Ошибка API: {error_text}"}), 500
        
    except Exception as e:
        error_msg = f"Ошибка сервера: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

@app.route('/test', methods=['GET'])
def test_api():
    """Тестовый endpoint для проверки API"""
    try:
        # Простой тест Prodia API
        response = requests.post("https://api.prodia.com/v1/sd/generate", json={
            "prompt": "test",
            "model": "dreamshaper_8.safetensors [9d40847d]",
            "steps": 5
        })
        return jsonify({
            "status": response.status_code,
            "message": "Prodia API доступен" if response.status_code == 200 else "Prodia API недоступен"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
