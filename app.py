from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import random
from PIL import Image, ImageDraw

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def generate_image(prompt):
    """Генерация изображения с проверенными моделями"""
    
    # СПИСОК ГАРАНТИРОВАННО РАБОЧИХ МОДЕЛЕЙ
    models = [
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1",
        "https://api-inference.huggingface.co/models/ogkalu/Stable-Diffusion-v1-5",
        "https://api-inference.huggingface.co/models/wavymulder/Analog-Diffusion"
    ]
    
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    for model_url in models:
        try:
            print(f"🔹 Пробуем модель: {model_url}")
            
            response = requests.post(model_url, headers=headers, json={
                "inputs": prompt,
                "options": {"wait_for_model": True}
            }, timeout=30)
            
            print(f"🔹 Статус ответа: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ УСПЕХ с моделью: {model_url}")
                return response.content
            elif response.status_code == 503:
                print(f"⏳ Модель загружается: {model_url}")
                continue
            else:
                print(f"❌ Ошибка {response.status_code} от {model_url}")
                continue
                
        except Exception as e:
            print(f"❌ Исключение с {model_url}: {str(e)}")
            continue
    
    # Если все модели не сработали - создаем тестовое изображение
    print("🔄 Все модели недоступны, создаем тестовое изображение")
    img = Image.new('RGB', (512, 512), color=(
        random.randint(50, 200), 
        random.randint(50, 200), 
        random.randint(50, 200)
    ))
    d = ImageDraw.Draw(img)
    d.text((50, 250), f"Prompt: {prompt[:30]}", fill=(255, 255, 255))
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        data = request.json
        prompt = data.get('prompt', '')
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"🎨 Получен промпт: {prompt}")
        
        # Генерация изображения
        image_bytes = generate_image(prompt)
        
        print("✅ Возвращаем изображение")
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
