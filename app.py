from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import base64
import time

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"Генерируем: {prompt}")
        
        # Вариант 1: Falcon API (бесплатный, без ключа)
        try:
            response = requests.post(
                "https://falcon-api.andrewmvd.com/generate",
                json={"prompt": prompt},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'image' in result:
                    image_data = result['image'].split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    return send_file(io.BytesIO(image_bytes), mimetype='image/png')
                    
        except Exception as e:
            print(f"Falcon API ошибка: {e}")
        
        # Вариант 2: LocalAI эмуляция
        try:
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": "Bearer free"},
                json={
                    "prompt": prompt,
                    "n": 1,
                    "size": "512x512"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                image_url = result['data'][0]['url']
                image_response = requests.get(image_url)
                return send_file(io.BytesIO(image_response.content), mimetype='image/png')
                
        except Exception as e:
            print(f"LocalAI ошибка: {e}")
        
        return jsonify({"error": "Все API временно недоступны"}), 500
        
    except Exception as e:
        return jsonify({"error": f"Ошибка: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
