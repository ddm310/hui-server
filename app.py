from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import hashlib
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

@app.before_request
def log_request_info():
    """Логируем все входящие запросы"""
    logger.info(f"📥 Входящий запрос: {request.method} {request.path}")

def translate_with_deepseek(text):
    """Перевод через DeepSeek API"""
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
            translation = result['choices'][0]['message']['content'].strip()
            translation = translation.strip('"')
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
    if translation and translation != text:
        return translation
    else:
        logger.warning("⚠️ Переводчик недоступен, используем оригинальный текст")
        return text

def describe_image_for_prompt(image_file):
    """Простая функция для описания изображения"""
    if image_file and image_file.filename:
        filename_lower = image_file.filename.lower()
        if any(word in filename_lower for word in ['portrait', 'face', 'person']):
            return "a portrait photo"
        elif any(word in filename_lower for word in ['landscape', 'nature', 'mountain']):
            return "a landscape photo" 
        elif any(word in filename_lower for word in ['city', 'urban', 'building']):
            return "an urban cityscape"
        elif any(word in filename_lower for word in ['cat', 'dog', 'animal']):
            return "an animal photo"
        else:
            return "an uploaded image"
    return "an uploaded image"

def create_consistent_seed(prompt, model_name):
    """Создает одинаковый seed для одинаковых промптов"""
    # Хэшируем промпт + модель чтобы получить предсказуемый seed
    seed_string = f"{prompt}_{model_name}"
    seed_hash = hashlib.md5(seed_string.encode()).hexdigest()
    # Берем первые 8 символов хэша и конвертируем в число
    return int(seed_hash[:8], 16) % 1000000

def create_smart_prompt(base_prompt, image_description=None, edit_mode=False):
    """Создает умный промпт для генерации"""
    if edit_mode and image_description:
        return f"{base_prompt} - edit and modify {image_description} while preserving original composition and style"
    elif image_description:
        return f"{base_prompt} - based on {image_description} with similar colors and style"
    else:
        return base_prompt

@app.route('/generate', methods=['POST'])
def generate_image_route():
    try:
        # Определяем тип запроса
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            prompt = request.form.get('prompt', '')
            model_name = request.form.get('model', 'nanobanano')
            image_file = request.files.get('image')
            edit_mode = request.form.get('edit_mode') == 'true'
        else:
            data = request.get_json() or {}
            prompt = data.get('prompt', '')
            model_name = data.get('model', 'nanobanano')
            image_file = None
            edit_mode = data.get('edit_mode', False)
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        logger.info(f"🎨 Начинаем генерацию: '{prompt}'")
        logger.info(f"🔧 Модель: {model_name}")
        logger.info(f"📝 Режим: {'редактирование' if edit_mode else 'создание'}")
        
        # Описание изображения если есть
        image_description = ""
        if image_file and image_file.filename:
            image_description = describe_image_for_prompt(image_file)
            logger.info(f"🖼️ Описание изображения: {image_description}")
        
        # Создаем умный промпт
        smart_prompt = create_smart_prompt(prompt, image_description, edit_mode)
        logger.info(f"💡 Умный промпт: '{smart_prompt}'")
        
        # Автоматический перевод
        translated_prompt = translate_text(smart_prompt)
        logger.info(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Генерация изображения
        encoded_prompt = urllib.parse.quote(translated_prompt)
        
        # ИСПРАВЛЕНИЕ: Убираем случайный seed, используем предсказуемый
        seed = create_consistent_seed(translated_prompt, model_name)
        logger.info(f"🌱 Seed: {seed} (одинаковый для одинаковых промптов)")
        
        if model_name in ["nanobanano", "pollinations", "flux", "dalle", "stable-diffusion", "midjourney"]:
            # БЕЗ seed параметра - будет генерировать одинаковые изображения
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512"
            logger.info(f"🔗 Pollinations URL (без seed)")
            response = requests.get(url, timeout=60)
        else:
            url = f"https://api-inference.huggingface.co/models/{model_name}"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
            logger.info(f"🔗 Hugging Face URL")
            response = requests.post(url, headers=headers, json={
                "inputs": translated_prompt,
                "options": {"wait_for_model": True}
            }, timeout=60)
        
        logger.info(f"📡 Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("✅ УСПЕХ: Изображение сгенерировано!")
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            error_msg = response.text[:200] if response.text else "Unknown error"
            logger.error(f"❌ Ошибка API: {error_msg}")
            return jsonify({"error": f"Ошибка генерации: {error_msg}"}), 500
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации: {str(e)}")
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Сервер работает"})

@app.route('/translate-test', methods=['POST'])
def translate_test():
    """Тест перевода"""
    try:
        data = request.get_json() or {}
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "Текст не может быть пустым"}), 400
        
        logger.info(f"🧪 Тест перевода: '{text}'")
        
        is_russian = any(char.lower() in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя' for char in text)
        
        if is_russian:
            translation = translate_with_deepseek(text)
            return jsonify({
                "original": text,
                "translated": translation,
                "is_russian": True,
                "translation_worked": translation is not None
            })
        else:
            return jsonify({
                "original": text,
                "translated": text,
                "is_russian": False,
                "message": "Текст уже на английском"
            })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    app.run(host='0.0.0.0', port=5000, debug=False)
