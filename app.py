from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def generate_with_pollinations(prompt):
    """Генерация через Pollinations.ai"""
    encoded_prompt = urllib.parse.quote(prompt)
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512"
    
    response = requests.get(pollinations_url, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Pollinations error: {response.status_code}")

def generate_with_huggingface(prompt, model_name):
    """Генерация через Hugging Face"""
    model_url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    response = requests.post(model_url, headers=headers, json={
        "inputs": prompt,
        "options": {"wait_for_model": True}
    })
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"HF error: {response.status_code} - {response.text}")

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        model_name = data.get('model', 'pollinations')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"🎨 Генерируем: {prompt}")
        print(f"🔧 Модель: {model_name}")
        
        if model_name == "pollinations":
            # Используем Pollinations.ai
            image_bytes = generate_with_pollinations(prompt)
        else:
            # Используем Hugging Face
            image_bytes = generate_with_huggingface(prompt, model_name)
        
        print("✅ УСПЕХ: Изображение сгенерировано!")
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
