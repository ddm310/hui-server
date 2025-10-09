from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        model_name = data.get('model', 'stabilityai/stable-diffusion-xl-base-1.0')  # Получаем модель из запроса
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"🎨 Генерируем: {prompt}")
        print(f"🔧 Модель: {model_name}")
        
        # Формируем URL для выбранной модели
        model_url = f"https://api-inference.huggingface.co/models/{model_name}"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        
        response = requests.post(model_url, headers=headers, json={
            "inputs": prompt,
            "options": {"wait_for_model": True}
        })
        
        print(f"🔹 Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ УСПЕХ: Изображение сгенерировано!")
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            error_msg = response.text[:500] if response.text else "Unknown error"
            print(f"❌ Ошибка API: {error_msg}")
            return jsonify({"error": f"Ошибка модели: {error_msg}"}), 500
        
    except Exception as e:
        error_msg = f"Ошибка генерации: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
