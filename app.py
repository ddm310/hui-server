from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def generate_image(prompt):
    """Генерация изображения с проверенной моделью"""
    
    # ГАРАНТИРОВАННО РАБОЧАЯ МОДЕЛЬ
    model_url = "https://api-inference.huggingface.co/models/StableDiffusionVN/Flux"
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    try:
        print(f"Пробуем модель: {model_url}")
        print(f"Промпт: {prompt}")
        print(f"API Key: {HF_API_KEY[:10]}...")  # Первые 10 символов ключа
        
        # Простой запрос без сложных параметров
        response = requests.post(model_url, headers=headers, json={
            "inputs": prompt,
            "options": {
                "wait_for_model": True,
                "use_cache": True
            }
        })
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ УСПЕХ: Изображение сгенерировано!")
            return response.content
        else:
            error_msg = response.text[:500] if response.text else "Unknown error"
            print(f"❌ Ошибка от модели: {error_msg}")
            raise Exception(f"Ошибка API: {error_msg}")
            
    except Exception as e:
        print(f"❌ Ошибка с моделью: {str(e)}")
        raise e

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        print("=== НАЧАЛО ГЕНЕРАЦИИ ===")
        print(f"API Key exists: {bool(HF_API_KEY)}")
        
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"Получен промпт: {prompt}")
        
        # Генерация изображения
        image_bytes = generate_image(prompt)
        
        print("✅ УСПЕХ: Возвращаем изображение")
        return send_file(
            io.BytesIO(image_bytes),
            mimetype='image/png'
        )
        
    except Exception as e:
        error_msg = f"Ошибка генерации: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

@app.route('/test', methods=['GET'])
def test():
    """Простой тест"""
    return jsonify({
        "api_key_exists": bool(HF_API_KEY),
        "api_key_length": len(HF_API_KEY) if HF_API_KEY else 0,
        "status": "ready"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
