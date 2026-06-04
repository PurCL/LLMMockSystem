#!/bin/bash

# MockVenv Manager Extension - 快速启动调试脚本

set -e

echo "🎯 MockVenv Manager Extension - 调试启动脚本"
echo "=============================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "package.json" ]; then
    echo "❌ 错误: 请在 vscode-extension 目录中运行此脚本"
    exit 1
fi

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

echo "✅ Node.js 版本: $(node --version)"
echo "✅ npm 版本: $(npm --version)"
echo ""

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📦 未找到 node_modules，正在安装依赖..."
    npm install
    echo ""
fi

# 编译代码
echo "🔨 编译 TypeScript 代码..."
npm run compile

if [ $? -eq 0 ]; then
    echo "✅ 编译成功！"
else
    echo "❌ 编译失败，请检查错误信息"
    exit 1
fi

vsce package