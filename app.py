from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import time

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def generate_image(prompt):
    """Генерация изображения с вашей моделью Kandinsky"""
    
    # Используем вашу модель Kandinsky с LoRA для покемонов
    model_url = "https://api-inference.huggingface.co/models/YiYiXu/kandinsky_2.2_decoder_lora_pokemon"
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    try:
        print(f"Пробуем модель: {model_url}")
        print(f"Промпт: {prompt}")
        
        response = requests.post(model_url, headers=headers, json={
            "inputs": prompt,
            "options": {
                "wait_for_model": True,
                "use_cache": True
            },
            "parameters": {
                "num_inference_steps": 25,
                "guidance_scale": 7.5
            }
        })
        
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            return response.content
        elif response.status_code == 503:
            # Модель загружается
            raise Exception("Модель загружается, попробуйте через 1-2 минуты")
        else:
            error_msg = response.text[:500] if response.text else "Unknown error"
            print(f"Ошибка от модели: {error_msg}")
            raise Exception(f"Ошибка API: {error_msg}")
            
    except Exception as e:
        print(f"Ошибка с моделью: {str(e)}")
        raise e

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
        test_url = "https://api-inference.huggingface.co/models/YiYiXu/kandinsky_2.2_decoder_lora_pokemon"
        
        response = requests.post(test_url, headers=headers, json={
            "inputs": "pikachu",
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
