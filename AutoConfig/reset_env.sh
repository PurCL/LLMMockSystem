#!/bin/bash

echo "🧹 1. 正在摧毁旧环境..."
rm -rf .venv

echo "🌱 2. 正在用 uv 极速重建虚拟环境..."
uv venv

echo "📦 3. 正在安装核心测试与 Agent 依赖..."
# 提示：安装 pytest-playwright 会自动把 pytest 和 playwright 一起装上
uv pip install claude-agent-sdk pytest-playwright

echo "🌐 4. 正在下载浏览器内核..."
# 需要先激活环境才能用 playwright 命令
source .venv/bin/activate
playwright install chromium

echo "🪝 5. 正在重新挂载 LLM 依赖自愈拦截器..."
python install_hook.py

echo "===================================================="
echo "✨ 黄金基线环境重置完毕！你可以开始下一轮纯净测试了。"
echo "请手动运行: source .venv/bin/activate"