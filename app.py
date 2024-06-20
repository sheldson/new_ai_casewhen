from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
import re

# 加载环境变量
load_dotenv()

# 配置日志记录
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# 设置 OpenAI API 密钥
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def parse_input(input_data, skip_header=False):
    logging.debug(f"解析输入数据: {input_data}")
    mappings = {}
    if isinstance(input_data, list):
        if skip_header:
            input_data = input_data[1:]  # 跳过表头
        for row in input_data:
            if len(row) == 2:
                key, value = row
                if key and value:
                    mappings[str(key).strip()] = str(value).strip()
    else:
        input_data = re.split(r'[，,]', input_data)
        for item in input_data:
            if re.search(r'[:：\s]', item):
                key, value = re.split(r'[:：\s]', item, 1)
                if key and value:
                    mappings[key.strip()] = value.strip()
            else:
                logging.error(f"行不包含预期的分隔符: {item}")
    logging.debug(f"解析的映射: {mappings}")
    return mappings

def generate_case_when_stream(mappings, field_name):
    prompt = f"Generate a SQL CASE WHEN statement for the field '{field_name}' with the following mappings:\n"
    for key, value in mappings.items():
        prompt += f"{key}: {value}\n"
    logging.debug(f"为 OpenAI 生成的提示: {prompt}")

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        stream=True,
    )

    def generate():
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                logging.debug(f"流式内容: {content}")
                yield content

    return generate()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-case-when', methods=['POST'])
def generate_case_when_endpoint():
    input_data = request.json.get('input')
    input_type = request.json.get('type')
    field_name = request.json.get('field_name')
    logging.debug(f"收到的输入数据: {input_data}")
    logging.debug(f"收到的字段名: {field_name}")
    try:
        skip_header = (input_type == 'upload')  # 仅在上传文件时跳过表头
        mappings = parse_input(input_data, skip_header)
        return Response(generate_case_when_stream(mappings, field_name), content_type='text/plain')
    except Exception as e:
        logging.error(f"处理请求时出错: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
