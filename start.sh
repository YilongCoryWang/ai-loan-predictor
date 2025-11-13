#!/bin/bash

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "警告：未激活虚拟环境。请考虑先运行 source /path/to/venv/bin/activate"
    # 如果您的虚拟环境名为 venv，并且位于项目根目录，可以尝试自动激活：
    # source venv/bin/activate
fi

# 检查 main:app 是否存在
if [ ! -f "main.py" ]; then
    echo "错误：未找到 main.py 文件。请确保脚本在项目根目录运行。"
    exit 1
fi

# 执行 Uvicorn 命令
# --host 0.0.0.0: 允许外部访问
# --port 8000: 监听端口 8000
# --reload: 启用文件更改时自动重载 (开发模式)
uvicorn main:app --host 0.0.0.0 --port 8000

echo "--- 停止运行 ---"