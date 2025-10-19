from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import os
import logging
import random
import urllib.parse
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Ключ Gemini для анализа изображений
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def translate_text(text):
    """Перевод через Google Translate"""
    if not any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text):
        return text
    
    logger.info(f"🧠 Перевод: '{text}'")
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'ru',
            'tl': 'en',
            'dt': 't',
            'q': text
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            translation = result[0][0][0]
            logger.info(f"✅ Перевел: '{translation}'")
            return translation
        else:
            return text
    except Exception as e:
        logger.warning(f"⚠️ Ошибка перевода: {e}")
        return text

def analyze_image_with_gemini(image_data, user_prompt):
    """Gemini анализирует изображение и создаёт детальный промпт"""
    try:
        if not GEMINI_API_KEY:
            logger.warning("❌ Нет Gemini API ключа")
            return user_prompt
            
        # Конвертируем изображение в base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        prompt_text = f"""
        Analyze this image and create a detailed image generation prompt that combines: "{user_prompt}" 
        with the visual content from the image. 
        
        Describe:
        - Main objects and their arrangement
        - Colors and lighting  
        - Style and composition
        - Key visual elements to preserve
        
        Return ONLY the prompt text in English, no additional explanations.
        """
        
        payload = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_b64
                        }
                    },
                    {
                        "text": prompt_text
                    }
                ]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            enhanced_prompt = result['choices'][0]['message']['content'].strip()
            logger.info(f"💡 Gemini создал промпт: {enhanced_prompt}")
            return enhanced_prompt
        else:
            logger.warning(f"⚠️ Gemini не сработал: {response.status_code}")
            return user_prompt
            
    except Exception as e:
        logger.error(f"❌ Ошибка Gemini: {e}")
        return user_prompt

def generate_with_pollinations(prompt, use_flux=True):
    """Генерация через Pollinations"""
    try:
        seed = random.randint(1, 1000000)
        
        if use_flux:
            # Используем FLUX для лучшего качества
            final_prompt = f"{prompt} --seed {seed} --model flux"
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_prompt)}"
        else:
            final_prompt = f"{prompt} --seed {seed}"
            url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(final_prompt)}"
        
        logger.info(f"🎯 Pollinations запрос: {final_prompt}")
        
        response = requests.get(url, timeout=45)
        
        if response.status_code == 200:
            logger.info("✅ Изображение сгенерировано!")
            return response.content
        else:
            logger.error(f"❌ Ошибка Pollinations: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка Pollinations: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        prompt = request.form.get('prompt', '')
        image_file = request.files.get('image')
        
        if not prompt:
            return jsonify({"error": "Введите описание"}), 400

        translated_prompt = translate_text(prompt)
        logger.info(f"🌐 Пользователь: '{prompt}' -> '{translated_prompt}'")

        # Если есть изображение - используем Gemini для анализа
        if image_file and image_file.filename:
            logger.info("🎨 Режим img2img с Gemini анализом")
            image_data = image_file.read()
            
            # Gemini анализирует изображение и создаёт детальный промпт
            enhanced_prompt = analyze_image_with_gemini(image_data, translated_prompt)
            
            # Генерируем через Pollinations Flux
            result = generate_with_pollinations(enhanced_prompt, use_flux=True)
            
        else:
            # Обычная генерация через Pollinations Flux
            logger.info("🆕 Обычная генерация через Flux")
            result = generate_with_pollinations(translated_prompt, use_flux=True)
        
        if result:
            return send_file(io.BytesIO(result), mimetype='image/png')
        else:
            return jsonify({"error": "Сервис генерации временно недоступен"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "OK", 
        "gemini_available": bool(GEMINI_API_KEY)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
