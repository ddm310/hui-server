from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import requests
import io
import base64
import urllib.parse
import random
import os
from dotenv import load_dotenv

# Загружаем переменные окружения для локальной разработки
load_dotenv()

app = Flask(__name__)
CORS(app)

def simple_working_version(prompt, image_data, strength=0.7):
    """Максимально простой но работающий вариант img2img"""
    try:
        print(f"🎨 Генерация будущего: {prompt}")
        
        # Создаем детальный промпт для "будущего через 10 лет"
        future_prompt = f"how this place will look in 10 years with {prompt}, futuristic, environmental changes, realistic vision, urban development"
        
        # Кодируем промпт для URL
        encoded_prompt = urllib.parse.quote(future_prompt)
        
        # Добавляем случайный seed для разнообразия
        seed = random.randint(1, 1000000)
        
        # Используем Pollinations с разными моделями
        models = ["flux", "nanobanano", "dalle"]
        
        for model in models:
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&model={model}&seed={seed}"
            
            print(f"🔄 Пробуем модель: {model}")
            response = requests.get(url, timeout=60)
            
            if response.status_code == 200:
                print(f"✅ Успех с моделью {model}!")
                return response.content
        
        return None
        
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Получаем данные из формы
        prompt = request.form.get('prompt', '')
        image_file = request.files.get('image')
        strength = float(request.form.get('strength', 0.7))
        
        print(f"📨 Получен запрос: {prompt}")
        print(f"💪 Сила изменений: {strength}")
        
        # Проверяем обязательные поля
        if not image_file:
            return {"error": "📸 Загрузите изображение места"}, 400
        
        if not prompt.strip():
            return {"error": "✍️ Опишите какие изменения хотите увидеть"}, 400
        
        # Читаем изображение
        image_data = image_file.read()
        print(f"🖼️ Изображение загружено: {len(image_data)} байт")
        
        # Генерируем изображение будущего
        result_image = simple_working_version(prompt, image_data, strength)
        
        if result_image:
            print("✅ Изображение будущего готово!")
            return send_file(
                io.BytesIO(result_image), 
                mimetype='image/png',
                as_attachment=False
            )
        else:
            print("❌ Не удалось сгенерировать изображение")
            return {"error": "Не удалось сгенерировать изображение. Попробуйте другой промпт."}, 500
            
    except Exception as e:
        print(f"💥 Ошибка сервера: {e}")
        return {"error": f"Ошибка сервера: {str(e)}"}, 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "OK", 
        "message": "Сервер работает!",
        "version": "1.0",
        "feature": "Генерация будущего через 10 лет"
    })

@app.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({
        "message": "Сервер отвечает!",
        "endpoints": {
            "health": "/health",
            "generate": "/generate (POST)"
        }
    })

if __name__ == '__main__':
    print("🚀 Сервер 'Будущее через 10 лет' запускается...")
    print("📍 Доступен по адресу: http://localhost:5000")
    print("🔧 Для проверки перейдите на: http://localhost:5000/health")
    app.run(host='0.0.0.0', port=5000, debug=True)
