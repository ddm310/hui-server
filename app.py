from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import requests
import io
import os
import logging
import random
import urllib.parse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Инициализируем Gemini клиент
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

def translate_with_deepseek(text):
    """Перевод через DeepSeek"""
    logger.info(f"🧠 Перевод: '{text}'")
    try:
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={'Content-Type': 'application/json'},
            json={
                'model': 'deepseek-chat',
                'messages': [
                    {
                        'role': 'system', 
                        'content': 'You are a professional translator. Translate Russian to English accurately. Return only the translation without any additional text.'
                    },
                    {
                        'role': 'user', 
                        'content': f'Translate this to English: "{text}"'
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 1000
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            translation = result['choices'][0]['message']['content'].strip().strip('"')
            logger.info(f"✅ Перевел: '{translation}'")
            return translation
        else:
            logger.error(f"❌ DeepSeek статус: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка перевода: {e}")
        return None

def translate_text(text):
    """Основная функция перевода"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
    translation = translate_with_deepseek(text)
    return translation if translation else text

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        prompt = request.form.get('prompt', '')
        image_file = request.files.get('image')
        
        if not prompt:
            return jsonify({"error": "Введите описание"}), 400

        # Переводим промпт
        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Оригинал: '{prompt}'")
        logger.info(f"🌐 Перевод: '{translated_prompt}'")

        # Если есть изображение - используем Gemini + Pollinations
        if image_file and image_file.filename:
            logger.info("🎨 Режим img2img через Gemini + Pollinations")
            
            # Читаем изображение
            image_data = image_file.read()
            image = Image.open(io.BytesIO(image_data))
            
            try:
                # Пробуем Gemini для анализа изображения
                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents=[
                        f"Analyze this image and create a detailed image generation prompt that combines: '{translated_prompt}' with the visual elements from this image. Return ONLY the prompt text.",
                        image
                    ],
                )
                
                enhanced_prompt = response.text.strip()
                logger.info(f"💡 Улучшенный промпт от Gemini: '{enhanced_prompt}'")
                
                # Добавляем случайность
                seed = random.randint(1, 1000000)
                final_prompt = f"{enhanced_prompt} --seed {seed}"
                
            except Exception as e:
                logger.warning(f"⚠️ Gemini анализ не сработал, используем оригинальный промпт: {e}")
                seed = random.randint(1, 1000000)
                final_prompt = f"{translated_prompt} --seed {seed}"
            
            # Генерируем через Pollinations
            encoded_prompt = urllib.parse.quote(final_prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
        else:
            # Обычная генерация
            logger.info("🆕 Обычная генерация через Pollinations")
            seed = random.randint(1, 1000000)
            final_prompt = f"{translated_prompt} --seed {seed}"
            encoded_prompt = urllib.parse.quote(final_prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=nanobanano"
        
        logger.info(f"🎯 Финальный промпт: '{final_prompt}'")
        
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            logger.info("✅ Изображение сгенерировано!")
            return send_file(io.BytesIO(response.content), mimetype='image/png')
        else:
            logger.error(f"❌ Ошибка генерации: {response.status_code}")
            return jsonify({"error": "Ошибка генерации"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
