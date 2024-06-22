from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
import re
import json
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Ensure OpenAI API key is set
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    logging.error("OPENAI_API_KEY environment variable is not set")
else:
    logging.debug(f"OPENAI_API_KEY is set")

client = OpenAI(api_key=api_key)

# Connect to the Supabase database
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def parse_input(input_data, skip_header=False):
    logging.debug(f"Parsing input data: {input_data}")
    mappings = {}
    input_fields = []
    if isinstance(input_data, list):
        if skip_header:
            input_data = input_data[1:]  # 跳过表头
        for row in input_data:
            if len(row) == 2:
                key, value = row
                if key and value:
                    mappings[str(key).strip()] = str(value).strip()
        input_fields = ["field_name"]
    else:
        input_data = re.split(r'[，,]', input_data)
        for item in input_data:
            if re.search(r'[:：\s]', item):
                key, value = re.split(r'[:：\s]', item, 1)
                if key and value:
                    mappings[key.strip()] = value.strip()
        input_fields = ["field_name"]
    logging.debug(f"Parsed mappings: {mappings}")
    return mappings, input_fields

def generate_case_when_stream(field_name, mappings):
    prompt = f"Generate a SQL CASE WHEN statement for the field '{field_name}' with the following mappings:\n. Only return SQL Statement which between three single quote"
    for key, value in mappings.items():
        prompt += f"{key}: {value}\n"
    logging.debug(f"Generated prompt for OpenAI: {prompt}")

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        stream=True,
    )

    def generate():
        try:
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                logging.debug(f"Streamed content: {content}")
                yield content
        except Exception as e:
            logging.error(f"Error generating CASE WHEN statement: {e}")
            yield f"Error generating CASE WHEN statement: {e}"

    return generate()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-case-when', methods=['POST'])
def generate_case_when_endpoint():
    input_data = request.json.get('input')
    input_type = request.json.get('type')
    field_name = request.json.get('field_name')
    user_id = request.json.get('user_id')
    logging.debug(f"Received input data: {input_data}")
    try:
        skip_header = (input_type == 'upload')  # 仅在上传文件时跳过表头
        mappings, input_fields = parse_input(input_data, skip_header)
        
        # 先插入一条记录
        data = {
            "user_id": user_id,
            "input_type": input_type,
            "model_output": "",
            "input_fields": [field_name],  # 确保字段名称正确
            "mappings": mappings  # 直接传递字典
        }
        insert_response = supabase.table('queries').insert(data).execute()
        query_id = insert_response.data[0]['id']
        
        # 使用流式响应生成 CASE WHEN 语句
        case_when_stream = generate_case_when_stream(field_name, mappings)
        
        def generate_with_update():
            model_output = ''
            try:
                for chunk in case_when_stream:
                    model_output += chunk
                    yield chunk
            finally:
                # 更新记录，加入生成的 CASE WHEN 语句
                update_data = {
                    "model_output": model_output,
                    "updated_at": 'now()'
                }
                supabase.table('queries').update(update_data).eq('id', query_id).execute()
        
        response = Response(generate_with_update(), content_type='text/plain')
        response.direct_passthrough = False
        return response
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
