from flask import Flask, request, send_file
from flask_cors import CORS
import requests
import io
import base64
import json
import os

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

if not OPENROUTER_API_KEY:
    print("❌ API ключ не найден!")

def analyze_with_claude(image_data, user_prompt):
    """Анализ изображения через Claude 3 Vision"""
    try:
        print("🔍 Анализируем изображение через Claude 3...")
        
        # Конвертируем изображение в base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # Промпт для Claude на русском
        system_prompt = """Ты - эксперт по урбанистике и футурологии. 
        Проанализируй изображение и опиши, как это место может выглядеть через 10 лет с учетом запроса пользователя.
        Верни ТОЛЬКО детальное описание на английском для генерации изображения, без лишних слов."""
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3-sonnet",  # Бесплатные запросы
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text",
                                "text": f"Пользователь просит: '{user_prompt}'. Опиши как это место будет выглядеть через 10 лет."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 500
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            description = result['choices'][0]['message']['content']
            print(f"✅ Claude анализ: {description}")
            return description
        else:
            print(f"❌ Ошибка Claude: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Ошибка анализа: {e}")
        return None

def generate_with_pollinations(prompt):
    """Генерация изображения через Pollinations"""
    try:
        print("🎨 Генерируем изображение...")
        
        # Кодируем промпт для URL
        import urllib.parse
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Используем Pollinations (бесплатно)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512"
        
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            print("✅ Изображение сгенерировано!")
            return response.content
        else:
            print(f"❌ Ошибка генерации: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"💥 Ошибка генерации: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate():
    try:
        # Получаем данные
        user_prompt = request.form.get('prompt', '')
        image_file = request.files.get('image')
        
        print(f"📨 Получен запрос: {user_prompt}")
        
        if not image_file:
            return {"error": "Загрузите изображение"}, 400
        
        # Читаем изображение
        image_data = image_file.read()
        
        # 1. Анализируем изображение через Claude
        detailed_prompt = analyze_with_claude(image_data, user_prompt)
        
        if not detailed_prompt:
            # Fallback - используем обычный промпт
            detailed_prompt = f"how this place will look in 10 years: {user_prompt}"
        
        # 2. Генерируем новое изображение
        result_image = generate_with_pollinations(detailed_prompt)
        
        if result_image:
            return send_file(io.BytesIO(result_image), mimetype='image/png')
        else:
            return {"error": "Не удалось сгенерировать изображение"}, 500
            
    except Exception as e:
        print(f"💥 Ошибка сервера: {e}")
        return {"error": f"Ошибка сервера: {str(e)}"}, 500

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "OK", "message": "Сервер работает!"}

if __name__ == '__main__':
    print("🚀 Сервер запущен на http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
