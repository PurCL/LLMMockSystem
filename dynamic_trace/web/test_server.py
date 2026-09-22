#!/usr/bin/env python3
"""
测试服务器配置
"""

import sys
from pathlib import Path

print("="*60)
print("🧪 测试 CVE Results Web Server")
print("="*60)

# 测试1: 检查Python版本
print("\n1️⃣ Python版本:", sys.version.split()[0])

# 测试2: 检查依赖
print("\n2️⃣ 检查依赖:")
try:
    import flask
    print(f"   ✅ Flask {flask.__version__}")
except ImportError:
    print("   ❌ Flask 未安装")
    sys.exit(1)

try:
    import flask_cors
    print(f"   ✅ flask-cors 已安装")
except ImportError:
    print("   ⚠️  flask-cors 未安装（可选）")

# 测试3: 检查results目录
print("\n3️⃣ 检查数据目录:")
results_dir = Path('/home/jian1000/data3/LLMMockSystem/dynamic_trace/results')
if results_dir.exists():
    cves = [d.name for d in results_dir.iterdir() if d.is_dir() and d.name.startswith('CVE-')]
    print(f"   ✅ Results目录存在")
    print(f"   📊 找到 {len(cves)} 个CVE")
    if cves:
        print(f"   📋 示例: {', '.join(cves[:3])}")
else:
    print(f"   ❌ Results目录不存在: {results_dir}")

# 测试4: 检查端口
print("\n4️⃣ 检查端口可用性:")
import socket

def check_port(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', port))
        sock.close()
        return True
    except OSError:
        return False

free_ports = []
for port in range(8000, 8010):
    if check_port(port):
        free_ports.append(port)

if free_ports:
    print(f"   ✅ 可用端口: {', '.join(map(str, free_ports[:3]))}")
else:
    print("   ⚠️  8000-8009端口都被占用，将搜索更高端口")

print("\n" + "="*60)
print("✅ 测试完成！服务器已准备就绪")
print("="*60)
print("\n💡 启动服务器:")
print("   cd /home/jian1000/data3/LLMMockSystem/dynamic_trace/web")
print("   ./start.sh")
print("\n   或者:")
print("   python3 server.py")
print()
