# CASE WHEN 语句生成器

这个项目是一个基于 Flask 和 Handsontable 的网页应用，帮助用户生成 SQL 的 `CASE WHEN` 语句。

## 安装步骤

1. 克隆仓库：

    ```bash
    git clone https://github.com/your-username/your-repository.git
    cd your-repository
    ```

2. 创建并激活虚拟环境：

    ```bash
    python -m venv env
    source env/bin/activate  # Windows 用户使用 `env\Scripts\activate`
    ```

3. 安装所需的包：

    ```bash
    pip install -r requirements.txt
    ```

4. 创建 `.env` 文件并添加你的 OpenAI API 密钥：

    ```plaintext
    OPENAI_API_KEY=your-openai-api-key
    ```

## 运行应用

1. 启动 Flask 应用：

    ```bash
    python app.py
    ```

2. 打开 `index.html` 文件在浏览器中查看网页。

## 使用方法

1. 在网页上手动录入、上传文件或粘贴映射关系。
2. 点击生成按钮生成 `CASE WHEN` 语句。

