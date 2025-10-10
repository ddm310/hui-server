def describe_image_for_prompt(image_file):
    """Простая функция для описания изображения (заглушка)"""
    # В реальности здесь можно использовать:
    # 1. AI для анализа изображения
    # 2. Предзаданные шаблоны
    # 3. Метаданные файла
    
    # Пока возвращаем общее описание на основе имени файла или размера
    if image_file and image_file.filename:
        if 'portrait' in image_file.filename.lower():
            return "a portrait photo"
        elif 'landscape' in image_file.filename.lower():
            return "a landscape photo" 
        elif 'city' in image_file.filename.lower():
            return "an urban cityscape"
        else:
            return "an uploaded image"
    return "an uploaded image"

@app.route('/generate-smart', methods=['POST'])
def generate_smart():
    """Умная генерация с псевдо-img2img"""
    try:
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            prompt = request.form.get('prompt', '')
            model_name = request.form.get('model', 'nanobanano')
            image_file = request.files.get('image')
        else:
            data = request.get_json()
            prompt = data.get('prompt', '') if data else ''
            model_name = data.get('model', 'nanobanano') if data else 'nanobanano'
            image_file = None
        
        if not prompt:
            return jsonify({"error": "Промпт не может быть пустым"}), 400
        
        print(f"📝 Промпт: '{prompt}'")
        
        # Если есть изображение, создаем улучшенный промпт
        image_description = ""
        if image_file and image_file.filename:
            image_description = describe_image_for_prompt(image_file)
            print(f"🖼️ Описание изображения: {image_description}")
        
        # Создаем финальный промпт
        if image_description:
            final_prompt = f"{prompt} - based on {image_description} maintaining similar style"
        else:
            final_prompt = prompt
        
        # Перевод промпта
        translated_prompt = translate_text(final_prompt)
        print(f"🌐 Переведенный промпт: '{translated_prompt}'")
        
        # Генерация
        encoded_prompt = requests.utils.quote(translated_prompt)
        seed = random.randint(1, 1000000)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model={model_name}&width=512&height=512&seed={seed}"
        
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            return send_file(
                io.BytesIO(response.content),
                mimetype='image/png'
            )
        else:
            return jsonify({"error": "Ошибка генерации"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
