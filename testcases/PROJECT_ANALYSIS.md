# ExecutionAgent 测试项目详细分析

## 下载完成情况

✅ **所有 50 个项目已成功下载**

- 下载时间: 2024-02-25
- 总大小: 由于使用 `--depth 1` 浅克隆，每个项目只包含最新快照
- 状态: 所有项目均成功克隆并分析

## 按语言分类统计

| 语言 | 项目数 | 目录位置 |
|------|--------|----------|
| Python | 11 | `projects/Python/` |
| JavaScript | 12 | `projects/Javascript/` |
| C | 10 | `projects/C/` |
| Java | 9 | `projects/Java/` |
| C++ | 8 | `projects/C++/` |

## 项目详细列表

### Python 项目 (11个)

| 项目名 | 测试元数据位置 |
|--------|---------------|
| pandas | `projects/Python/pandas/test_metadata.json` |
| scikit-learn | `projects/Python/scikit_learn/test_metadata.json` |
| scipy | `projects/Python/scipy/test_metadata.json` |
| numpy | `projects/Python/numpy/test_metadata.json` |
| django | `projects/Python/django/test_metadata.json` |
| langchain | `projects/Python/langchain/test_metadata.json` |
| pytest | `projects/Python/pytest/test_metadata.json` |
| cpython | `projects/Python/cpython/test_metadata.json` |
| ansible | `projects/Python/ansible/test_metadata.json` |
| flask | `projects/Python/flask/test_metadata.json` |
| keras | `projects/Python/keras/test_metadata.json` |

### Java 项目 (9个)

| 项目名 | 测试元数据位置 |
|--------|---------------|
| flink | `projects/Java/flink/test_metadata.json` |
| commons-csv | `projects/Java/commons_csv/test_metadata.json` |
| dubbo | `projects/Java/dubbo/test_metadata.json` |
| mybatis-3 | `projects/Java/mybatis_3/test_metadata.json` |
| rocketmq | `projects/Java/rocketmq/test_metadata.json` |
| guava | `projects/Java/guava/test_metadata.json` |
| RxJava | `projects/Java/rxjava/test_metadata.json` |
| Activiti | `projects/Java/activiti/test_metadata.json` |
| spring-security | `projects/Java/spring_security/test_metadata.json` |

### JavaScript 项目 (12个)

| 项目名 | 测试元数据位置 |
|--------|---------------|
| react | `projects/Javascript/react/test_metadata.json` |
| vue | `projects/Javascript/vue/test_metadata.json` |
| bootstrap | `projects/Javascript/bootstrap/test_metadata.json` |
| node | `projects/Javascript/node/test_metadata.json` |
| axios | `projects/Javascript/axios/test_metadata.json` |
| typescript | `projects/Javascript/typescript/test_metadata.json` |
| deno | `projects/Javascript/deno/test_metadata.json` |
| mermaid | `projects/Javascript/mermaid/test_metadata.json` |
| nest | `projects/Javascript/nest/test_metadata.json` |
| webpack | `projects/Javascript/webpack/test_metadata.json` |
| express | `projects/Javascript/express/test_metadata.json` |
| Chart.js | `projects/Javascript/chart_js/test_metadata.json` |

### C 项目 (10个)

| 项目名 | 测试元数据位置 |
|--------|---------------|
| git | `projects/C/git/test_metadata.json` |
| mpv | `projects/C/mpv/test_metadata.json` |
| FreeRTOS-Kernel | `projects/C/freertos_kernel/test_metadata.json` |
| ccache | `projects/C/ccache/test_metadata.json` |
| msgpack-c | `projects/C/msgpack_c/test_metadata.json` |
| openvpn | `projects/C/openvpn/test_metadata.json` |
| distcc | `projects/C/distcc/test_metadata.json` |
| xrdp | `projects/C/xrdp/test_metadata.json` |
| libevent | `projects/C/libevent/test_metadata.json` |
| json-c | `projects/C/json_c/test_metadata.json` |

### C++ 项目 (8个)

| 项目名 | 测试元数据位置 |
|--------|---------------|
| tensorflow | `projects/C++/tensorflow/test_metadata.json` |
| react-native | `projects/C++/react_native/test_metadata.json` |
| opencv | `projects/C++/opencv/test_metadata.json` |
| imgui_test_engine | `projects/C++/imgui_test_engine/test_metadata.json` |
| folly | `projects/C++/folly/test_metadata.json` |
| xgboost | `projects/C++/xgboost/test_metadata.json` |
| webview | `projects/C++/webview/test_metadata.json` |
| json | `projects/C++/json/test_metadata.json` |

## 测试元数据说明

每个项目的 `test_metadata.json` 文件包含：

```json
{
  "project_name": "项目名称",
  "project_url": "GitHub仓库URL",
  "language": "编程语言",
  "project_path": "本地路径",
  "test_directories": ["测试目录列表"],
  "test_config_files": ["测试配置文件列表"],
  "downloaded_at": "下载时间戳"
}
```

## 如何使用这些项目

### 1. 查看特定项目的测试信息

```bash
# 查看 pandas 项目的测试元数据
cat projects/Python/pandas/test_metadata.json | python3 -m json.tool
```

### 2. 列出所有测试目录

```bash
# 查看所有 Python 项目的测试目录
find projects/Python -name "test_metadata.json" -exec cat {} \; | grep -A 1 "test_directories"
```

### 3. 统计测试文件数量

```bash
# 统计某个项目的测试文件数量（以 Python 为例）
find projects/Python/pandas -name "test_*.py" -o -name "*_test.py" | wc -l
```

### 4. 配合 ExecutionAgent 使用

```bash
# 进入 ExecutionAgent 目录
cd ../ExecutionAgent

# 运行单个项目
python3 launcher.py --run pandas --verbose

# 运行特定语言的所有项目
python3 launcher.py --run python --verbose

# 并行运行多个项目
python3 launcher.py --run python --parallel 4 --verbose
```

## 常见测试模式

### Python 项目
- **测试框架**: pytest, unittest
- **测试目录**: `tests/`, `test/`
- **测试文件命名**: `test_*.py`, `*_test.py`
- **配置文件**: `pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.py`

### Java 项目
- **测试框架**: JUnit, TestNG
- **测试目录**: `src/test/java/`
- **测试文件命名**: `*Test.java`, `*Tests.java`
- **构建工具**: Maven (`pom.xml`), Gradle (`build.gradle`)

### JavaScript 项目
- **测试框架**: Jest, Mocha, Jasmine
- **测试目录**: `test/`, `tests/`, `__tests__/`, `spec/`
- **测试文件命名**: `*.test.js`, `*.spec.js`, `*.test.ts`
- **配置文件**: `package.json`, `jest.config.js`

### C/C++ 项目
- **测试框架**: GoogleTest, Catch2, CTest
- **测试目录**: `test/`, `tests/`
- **构建系统**: Make (`Makefile`), CMake (`CMakeLists.txt`)

## 注意事项

1. **浅克隆**: 所有项目都使用 `git clone --depth 1` 下载，只包含最新版本，不包含完整历史记录
2. **测试识别**: 测试目录和文件的识别基于常见命名模式，可能不完整
3. **大型项目**: 如 tensorflow, flink 等项目包含大量测试，可能需要较长时间运行
4. **依赖安装**: 运行测试前需要先安装项目依赖
5. **环境要求**: 某些项目可能需要特定的系统依赖或编译工具

## 快速导航

```bash
# 查看目录结构
tree -L 2 ExecutionAgent_TestProjects/

# 查看每个语言的项目列表
ls projects/Python/
ls projects/Java/
ls projects/Javascript/
ls projects/C/
ls projects/C++/

# 统计总大小
du -sh projects/

# 查看完整的下载摘要
cat projects/download_summary.json | python3 -m json.tool
```

## 相关文件

- `README.md` - 项目概览和使用说明
- `download_projects.py` - 下载脚本源代码
- `download_log.txt` - 完整下载日志
- `projects/download_summary.json` - 所有项目的详细元数据

---

**创建日期**: 2024-02-25
**数据来源**: [ExecutionAgent GitHub Repository](https://github.com/sola-st/ExecutionAgent)
