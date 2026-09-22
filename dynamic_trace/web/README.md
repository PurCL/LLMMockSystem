# 🛡️ CVE Results Web Server

一个用于展示 LLMMockSystem 动态追踪结果的Web服务器。

## 📁 项目结构

```
web/
├── server.py              # Flask Web服务器主程序
├── templates/             # HTML模板目录
│   ├── base.html         # 基础模板
│   ├── index.html        # 首页 - CVE列表
│   └── cve_detail.html   # CVE详情页
├── requirements.txt       # Python依赖
├── start.sh              # 启动脚本
└── README.md             # 本文档
```

## ⚙️ 功能特性

- ✅ 自动扫描并展示所有CVE目录
- ✅ 美观的响应式Web界面
- ✅ 实时搜索过滤CVE
- ✅ 在线查看JSON文件内容
- ✅ 文件下载功能
- ✅ 自动查找空闲端口（8000-9000）
- ✅ RESTful API支持

## 🚀 快速开始

### 方法1: 使用启动脚本（推荐）

```bash
cd /home/jian1000/data3/LLMMockSystem/dynamic_trace/web
./start.sh
```

### 方法2: 直接运行Python

```bash
cd /home/jian1000/data3/LLMMockSystem/dynamic_trace/web

# 安装依赖
pip3 install -r requirements.txt --user

# 启动服务器
python3 server.py
```

## 🌐 访问地址

服务器启动后，会自动查找空闲端口并显示访问地址：

```
🚀 CVE Results Web Server Starting...
📁 Results Directory: /home/jian1000/data3/LLMMockSystem/dynamic_trace/results
🌐 Server URL: http://localhost:8000
```

在浏览器中打开显示的URL即可访问。

## 📚 API接口

### 获取所有CVE列表
```
GET /api/cves
```

响应示例：
```json
{
  "cves": ["CVE-2024-0520", "CVE-2026-1462", ...],
  "total": 28
}
```

### 获取CVE详细信息
```
GET /api/cve/<cve_id>
```

响应示例：
```json
{
  "cve_id": "CVE-2024-0520",
  "files": [...],
  "data": {
    "compatibility": {...},
    "exploit_test_results": {...},
    "statistics": {...}
  }
}
```

### 获取特定文件内容
```
GET /api/cve/<cve_id>/file/<filename>
```

### 下载文件
```
GET /download/<cve_id>/<filename>
```

## 🎨 界面功能

### 首页
- 显示所有CVE的卡片视图
- 实时搜索框（支持 `/` 快捷键快速聚焦）
- 显示总CVE数量统计

### CVE详情页
- 显示该CVE下所有文件
- 在线查看JSON文件（美化格式）
- 下载文件功能
- 支持 `ESC` 键关闭文件查看器

## 🔧 配置说明

如需修改结果目录路径，编辑 `server.py` 中的 `RESULTS_DIR` 变量：

```python
RESULTS_DIR = Path('/home/jian1000/data3/LLMMockSystem/dynamic_trace/results')
```

如需修改端口范围，编辑 `find_free_port()` 函数参数：

```python
port = find_free_port(start_port=8000, end_port=9000)
```

## 📝 系统要求

- Python 3.7+
- Flask 3.0.0
- flask-cors 4.0.0

## 🐛 故障排除

### 端口被占用
服务器会自动查找8000-9000范围内的空闲端口。如果所有端口都被占用，会显示错误信息。

### 依赖安装失败
使用 `--user` 参数安装到用户目录：
```bash
pip3 install -r requirements.txt --user
```

### 文件权限问题
确保有读取results目录的权限：
```bash
ls -la /home/jian1000/data3/LLMMockSystem/dynamic_trace/results
```

## 📄 许可证

此项目为 LLMMockSystem 的一部分。

---

**开发时间**: 2024
**版本**: 1.0.0
