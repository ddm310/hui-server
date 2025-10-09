from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import io
import urllib.parse
import os
import random
import json

app = Flask(__name__)
CORS(app)

HF_API_KEY = os.getenv('HF_API_KEY')

def translate_to_english(text):
    """Переводит русский текст на английский используя бесплатный API"""
    try:
        # Простой переводчик через LibreTranslate (бесплатный)
        response = requests.post(
            'https://libretranslate.de/translate',
            json={
                'q': text,
                'source': 'ru',
                'target': 'en',
                'format': 'text'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['translatedText']
        else:
            # Если LibreTranslate не работает, пробуем MyMemory
            return translate_with_mymemory(text)
            
    except Exception as e:
        print(f"⚠️ Ошибка перевода: {e}")
        # Возвращаем оригинальный текст если перевод не удался
        return text

def translate_with_mymemory(text):
    """Резервный переводчик"""
    try:
        response = requests.get(
            f"https://api.mymemory.translated.net/get",
            params={
                'q': text,
                'langpair': 'ru|en'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['responseData']['translatedText']
        return text
    except:
        return text

def is_russian_text(text):
    """Проверяет содержит ли текст русские буквы"""
    russian_letters = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')
    return any(char.lower() in russian_letters for char in text)

def generate_with_pollinations(prompt, model="pollinations", use_translation=True):
    """Генерация через Pollinations.ai с автоматическим переводом"""
    
    # Автоматически переводим русский текст
    final_prompt = prompt
    if use_translation and is_russian_text(prompt):
        print(f"🔤 Переводчик: '{prompt}' -> ", end="")
        final_prompt = translate_to_english(prompt)
        print(f"'{final_prompt}'")
    
    encoded_prompt = urllib.parse.quote(final_prompt)
    seed = random.randint(1, 1000000)
    
    models = {
        "pollinations": "pollinations",
        "flux": "flux", 
        "dalle": "dalle"
    }
    
    selected_model = models.get(model, "pollinations")
    
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={selected_model}&width=512&height=512&seed={seed}&nofilter=true"
    
    print(f"🔧 Модель: {selected_model}, seed: {seed}")
    response = requests.get(pollinations_url, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Pollinations error: {response.status_code}")

def generate_with_huggingface(prompt, model_name, use_translation=True):
    """Генерация через Hugging Face с переводом"""
    
    # Автоматически переводим русский текст
    final_prompt = prompt
    if use_translation and is_russian_text(prompt):
        print(f"🔤 Переводчик: '{prompt}' -> ", end="")
        final_prompt = translate_to_english(prompt)
        print(f"'{final_prompt}'")
    
    model_url = f"https://api-inference.huggingface.co/models/{model_name}"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    
    response = requests.post(model_url, headers=headers, json={
        "inputs": final_prompt,
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
        
        print(f"🎨 Оригинальный промпт: {prompt}")
        print(f"🔧 Модель: {model_name}")
        
        # Все модели теперь с автоматическим переводом
        if model_name in ["pollinations", "flux", "dalle"]:
            image_bytes = generate_with_pollinations(prompt, model_name, use_translation=True)
        else:
            image_bytes = generate_with_huggingface(prompt, model_name, use_translation=True)
        
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

@app.route('/translate-test', methods=['POST'])
def translate_test():
    """Тестовый endpoint для проверки перевода"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "Текст не может быть пустым"}), 400
        
        translated = translate_to_english(text)
        
        return jsonify({
            "original": text,
            "translated": translated,
            "is_russian": is_russian_text(text)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
