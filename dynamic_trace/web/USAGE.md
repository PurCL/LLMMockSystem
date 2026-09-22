# 📖 CVE Results Web Server - 使用手册

## 🚀 启动服务器

### 快速启动

```bash
cd /home/jian1000/data3/LLMMockSystem/dynamic_trace/web
./start.sh
```

或者：

```bash
cd /home/jian1000/data3/LLMMockSystem/dynamic_trace/web
python3 server.py
```

## 🌐 访问界面

启动后，终端会显示：

```
============================================================
🚀 CVE Results Web Server Starting...
============================================================
📁 Results Directory: /home/jian1000/data3/LLMMockSystem/dynamic_trace/results
🌐 Server URL: http://localhost:8000
============================================================
```

在浏览器中访问显示的URL（例如：http://localhost:8000）

## 🎯 功能说明

### 1. 首页 - CVE列表

**功能：**
- 显示所有CVE的卡片视图
- 显示CVE总数统计
- 实时搜索功能

**操作：**
- 点击任意CVE卡片进入详情页
- 在搜索框中输入CVE ID进行过滤
- 按 `/` 键快速聚焦到搜索框

**示例：**
- 搜索 "2026" 会显示所有包含2026的CVE
- 搜索 "CVE-2024" 会显示2024年的CVE

### 2. CVE详情页

**功能：**
- 显示该CVE下的所有文件
- 在线查看JSON文件内容
- 下载文件

**操作：**
- 点击 "👁️ 查看" 按钮在线查看JSON文件
- 点击 "⬇️ 下载" 按钮下载文件
- 点击 "← 返回首页" 返回CVE列表

**查看器功能：**
- 自动格式化JSON内容
- 语法高亮显示
- 按 `ESC` 键关闭查看器
- 点击背景区域关闭查看器

### 3. 文件类型

每个CVE目录通常包含以下文件：

| 文件名 | 说明 |
|--------|------|
| `*-compatibility.json` | 兼容性测试结果 |
| `*-exploit_test_results.json` | 漏洞利用测试结果 |
| `*-statistics.json` | 统计信息 |

## 🔧 配置选项

### 修改端口范围

编辑 `server.py` 第16-17行：

```python
def find_free_port(start_port=8000, end_port=9000):
```

### 修改数据目录

编辑 `server.py` 第23行：

```python
RESULTS_DIR = Path('/your/custom/path')
```

### 修改服务器地址

编辑 `server.py` 最后一行：

```python
app.run(host='0.0.0.0', port=port, debug=True)
```

- `host='0.0.0.0'` - 允许外部访问
- `host='127.0.0.1'` - 仅本地访问
- `debug=True` - 开发模式（自动重载）
- `debug=False` - 生产模式

## 🔌 API接口使用

### 获取所有CVE

```bash
curl http://localhost:8000/api/cves
```

返回：
```json
{
  "cves": ["CVE-2024-0520", "CVE-2026-1462", ...],
  "total": 26
}
```

### 获取CVE详情

```bash
curl http://localhost:8000/api/cve/CVE-2024-0520
```

返回：
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

### 获取特定文件

```bash
curl http://localhost:8000/api/cve/CVE-2024-0520/file/CVE-2024-0520-statistics.json
```

### 下载文件

```bash
curl -O http://localhost:8000/download/CVE-2024-0520/CVE-2024-0520-statistics.json
```

## ⌨️ 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `/` | 聚焦到搜索框（首页） |
| `ESC` | 关闭文件查看器（详情页） |

## 🐛 常见问题

### Q: 端口被占用怎么办？

A: 服务器会自动查找8000-9000范围内的空闲端口。如果需要指定端口：

```python
# 编辑 server.py，在最后添加：
port = 8888  # 指定端口
app.run(host='0.0.0.0', port=port, debug=True)
```

### Q: 无法访问服务器？

A: 检查以下几点：
1. 确认服务器已启动且没有错误
2. 检查防火墙设置
3. 确认使用正确的URL和端口
4. 如果是远程访问，确保 host 设置为 '0.0.0.0'

### Q: JSON文件显示乱码？

A: 确保文件是UTF-8编码。服务器默认使用UTF-8读取文件。

### Q: 文件列表为空？

A: 检查：
1. Results目录路径是否正确
2. CVE目录下是否有文件
3. 是否有读取权限

```bash
ls -la /home/jian1000/data3/LLMMockSystem/dynamic_trace/results/CVE-2024-0520/
```

### Q: 如何停止服务器？

A: 在终端按 `Ctrl + C`

## 📊 性能优化

### 处理大量CVE

如果CVE数量很多（>100），建议：

1. 增加分页功能
2. 使用虚拟滚动
3. 启用缓存

### 处理大文件

对于大型JSON文件（>5MB），建议：

1. 使用流式加载
2. 增加分页显示
3. 提供下载而非在线查看

## 🔒 安全建议

**⚠️ 重要：此服务器仅用于本地开发！**

如需在生产环境使用：

1. 使用生产级WSGI服务器（如Gunicorn）
2. 配置反向代理（如Nginx）
3. 启用HTTPS
4. 添加访问控制
5. 关闭调试模式

示例（使用Gunicorn）：

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 server:app
```

## 📞 技术支持

如有问题，请检查：

1. 服务器日志输出
2. 浏览器控制台（F12）
3. 文件权限和路径

---

**版本**: 1.0.0
**更新时间**: 2024-09-22
