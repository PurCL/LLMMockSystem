# ExecutionAgent Test Projects Collection

这个目录包含了从 [ExecutionAgent](https://github.com/sola-st/ExecutionAgent) 项目中提取的所有50个用于测试的开源项目及其测试用例。

## 项目概览

ExecutionAgent 是一个自动化系统，用于在 Docker 容器内设置、构建和运行软件项目的测试套件。本集合包含了该项目用于评估的所有测试项目。

### 项目统计

- **总项目数**: 50
- **Python 项目**: 11
- **Java 项目**: 9
- **JavaScript 项目**: 12
- **C 项目**: 10
- **C++ 项目**: 8

## 目录结构

```
ExecutionAgent_TestProjects/
├── README.md                    # 本文档
├── download_projects.py         # 下载脚本
├── download_log.txt            # 下载日志
├── download_summary.json       # 下载摘要
└── projects/                   # 所有项目的源代码
    ├── Python/                 # Python 项目
    │   ├── pandas/
    │   │   ├── test_metadata.json
    │   │   └── [源代码]
    │   ├── scikit_learn/
    │   ├── scipy/
    │   ├── numpy/
    │   ├── django/
    │   ├── langchain/
    │   ├── pytest/
    │   ├── cpython/
    │   ├── ansible/
    │   ├── flask/
    │   └── keras/
    ├── Java/                   # Java 项目
    │   ├── flink/
    │   ├── commons_csv/
    │   ├── dubbo/
    │   ├── mybatis_3/
    │   ├── rocketmq/
    │   ├── guava/
    │   ├── rxjava/
    │   ├── activiti/
    │   └── spring_security/
    ├── Javascript/             # JavaScript 项目
    │   ├── react/
    │   ├── vue/
    │   ├── bootstrap/
    │   ├── node/
    │   ├── axios/
    │   ├── typescript/
    │   ├── deno/
    │   ├── mermaid/
    │   ├── nest/
    │   ├── webpack/
    │   ├── express/
    │   └── chart_js/
    ├── C/                      # C 项目
    │   ├── git/
    │   ├── mpv/
    │   ├── freertos_kernel/
    │   ├── ccache/
    │   ├── msgpack_c/
    │   ├── openvpn/
    │   ├── distcc/
    │   ├── xrdp/
    │   ├── libevent/
    │   └── json_c/
    └── C++/                    # C++ 项目
        ├── tensorflow/
        ├── react_native/
        ├── opencv/
        ├── imgui_test_engine/
        ├── folly/
        ├── xgboost/
        ├── webview/
        └── json/
```

## 项目列表

### Python 项目 (11)

| # | 项目名 | GitHub URL | 描述 |
|---|--------|-----------|------|
| 1 | pandas | https://github.com/pandas-dev/pandas | 数据分析库 |
| 2 | scikit-learn | https://github.com/scikit-learn/scikit-learn | 机器学习库 |
| 3 | scipy | https://github.com/scipy/scipy | 科学计算库 |
| 4 | numpy | https://github.com/numpy/numpy | 数值计算库 |
| 5 | django | https://github.com/django/django | Web框架 |
| 6 | langchain | https://github.com/langchain-ai/langchain | LLM应用框架 |
| 7 | pytest | https://github.com/pytest-dev/pytest | 测试框架 |
| 8 | cpython | https://github.com/python/cpython | Python解释器 |
| 9 | ansible | https://github.com/ansible/ansible | 自动化运维工具 |
| 10 | flask | https://github.com/pallets/flask | 轻量级Web框架 |
| 11 | keras | https://github.com/keras-team/keras | 深度学习框架 |

### Java 项目 (9)

| # | 项目名 | GitHub URL |
|---|--------|-----------|
| 1 | flink | https://github.com/apache/flink |
| 2 | commons-csv | https://github.com/apache/commons-csv |
| 3 | dubbo | https://github.com/apache/dubbo |
| 4 | mybatis-3 | https://github.com/mybatis/mybatis-3 |
| 5 | rocketmq | https://github.com/apache/rocketmq |
| 6 | guava | https://github.com/google/guava |
| 7 | RxJava | https://github.com/ReactiveX/RxJava |
| 8 | Activiti | https://github.com/Activiti/Activiti |
| 9 | spring-security | https://github.com/spring-projects/spring-security |

### JavaScript 项目 (12)

| # | 项目名 | GitHub URL |
|---|--------|-----------|
| 1 | react | https://github.com/facebook/react |
| 2 | vue | https://github.com/vuejs/vue |
| 3 | bootstrap | https://github.com/twbs/bootstrap |
| 4 | node | https://github.com/nodejs/node |
| 5 | axios | https://github.com/axios/axios |
| 6 | typescript | https://github.com/microsoft/TypeScript |
| 7 | deno | https://github.com/denoland/deno |
| 8 | mermaid | https://github.com/mermaid-js/mermaid |
| 9 | nest | https://github.com/nestjs/nest |
| 10 | webpack | https://github.com/webpack/webpack |
| 11 | express | https://github.com/expressjs/express |
| 12 | Chart.js | https://github.com/chartjs/Chart.js |

### C 项目 (10)

| # | 项目名 | GitHub URL |
|---|--------|-----------|
| 1 | git | https://github.com/git/git |
| 2 | mpv | https://github.com/mpv-player/mpv |
| 3 | FreeRTOS-Kernel | https://github.com/FreeRTOS/FreeRTOS-Kernel |
| 4 | ccache | https://github.com/ccache/ccache |
| 5 | msgpack-c | https://github.com/msgpack/msgpack-c |
| 6 | openvpn | https://github.com/OpenVPN/openvpn |
| 7 | distcc | https://github.com/distcc/distcc |
| 8 | xrdp | https://github.com/neutrinolabs/xrdp |
| 9 | libevent | https://github.com/libevent/libevent |
| 10 | json-c | https://github.com/json-c/json-c |

### C++ 项目 (8)

| # | 项目名 | GitHub URL |
|---|--------|-----------|
| 1 | tensorflow | https://github.com/tensorflow/tensorflow |
| 2 | react-native | https://github.com/facebook/react-native |
| 3 | opencv | https://github.com/opencv/opencv |
| 4 | imgui_test_engine | https://github.com/ocornut/imgui_test_engine |
| 5 | folly | https://github.com/facebook/folly |
| 6 | xgboost | https://github.com/dmlc/xgboost |
| 7 | webview | https://github.com/webview/webview |
| 8 | json | https://github.com/nlohmann/json |

## 测试用例信息

每个项目目录包含：

1. **源代码**: 完整的项目源代码（使用 `git clone --depth 1` 获取最新版本）
2. **test_metadata.json**: 测试元数据文件，包含：
   - 项目名称和URL
   - 编程语言
   - 测试目录列表
   - 测试配置文件列表（如 pytest.ini, pom.xml, package.json 等）
   - 下载时间戳

### 测试目录和配置文件

脚本会自动识别以下内容：

#### Python 项目
- 测试目录: `test/`, `tests/`, `testing/`
- 配置文件: `pytest.ini`, `setup.py`, `pyproject.toml`, `tox.ini`, `setup.cfg`

#### Java 项目
- 测试目录: `test/`, `tests/`
- 配置文件: `pom.xml`, `build.gradle`, `build.xml`

#### JavaScript 项目
- 测试目录: `test/`, `tests/`, `__tests__/`, `spec/`, `specs/`
- 配置文件: `package.json`, `jest.config.js`, `karma.conf.js`

#### C/C++ 项目
- 测试目录: `test/`, `tests/`, `testing/`
- 配置文件: `Makefile`, `CMakeLists.txt`, `configure.ac`, `meson.build`

## 使用说明

### 查看项目测试信息

```bash
# 查看某个项目的测试元数据
cat projects/Python/pandas/test_metadata.json
```

### 运行测试

每个项目的测试运行方式不同，请参考各项目的测试元数据和配置文件。

### 重新下载项目

```bash
# 运行下载脚本
python3 download_projects.py
```

脚本会自动跳过已存在的项目，只下载缺失的项目。

## 与 ExecutionAgent 集成

这些项目可以直接用于 ExecutionAgent 的测试：

```bash
# 使用 ExecutionAgent 的 launcher
cd ../ExecutionAgent
python launcher.py --run scipy  # 运行单个项目
python launcher.py --run python  # 运行所有 Python 项目
python launcher.py --run all     # 运行所有项目
```

## 文件说明

- **download_projects.py**: 自动化下载脚本，会克隆所有50个项目并分析测试结构
- **download_summary.json**: 包含所有项目的下载摘要和统计信息
- **download_log.txt**: 下载过程的完整日志

## 注意事项

1. 所有项目使用 `--depth 1` 进行浅克隆以节省空间和时间
2. 某些大型项目（如 tensorflow, opencv）可能需要较长下载时间
3. 测试目录和配置文件的识别基于常见模式，可能不完全准确
4. 建议参考各项目的官方文档了解如何运行测试

## 许可证

每个项目都遵循其各自的开源许可证，请参考各项目目录中的 LICENSE 文件。

## 引用

如果您使用这些测试项目进行研究，请引用 ExecutionAgent 原始项目：

```
ExecutionAgent: https://github.com/sola-st/ExecutionAgent
```

---

**生成时间**: 2024-02-25
**来源**: ExecutionAgent Project (https://github.com/sola-st/ExecutionAgent)
