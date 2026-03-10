#!/usr/bin/env python3
"""
Script to download all ExecutionAgent test projects and organize their test cases.
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Project definitions from launcher.py
PROJECTS = [
    # Python Projects (11)
    {"name": "pandas", "url": "https://github.com/pandas-dev/pandas", "language": "Python"},
    {"name": "scikit-learn", "url": "https://github.com/scikit-learn/scikit-learn", "language": "Python"},
    {"name": "scipy", "url": "https://github.com/scipy/scipy", "language": "Python"},
    {"name": "numpy", "url": "https://github.com/numpy/numpy", "language": "Python"},
    {"name": "django", "url": "https://github.com/django/django", "language": "Python"},
    {"name": "langchain", "url": "https://github.com/langchain-ai/langchain", "language": "Python"},
    {"name": "pytest", "url": "https://github.com/pytest-dev/pytest", "language": "Python"},
    {"name": "cpython", "url": "https://github.com/python/cpython", "language": "Python"},
    {"name": "ansible", "url": "https://github.com/ansible/ansible", "language": "Python"},
    {"name": "flask", "url": "https://github.com/pallets/flask", "language": "Python"},
    {"name": "keras", "url": "https://github.com/keras-team/keras", "language": "Python"},

    # Java Projects (9)
    {"name": "flink", "url": "https://github.com/apache/flink", "language": "Java"},
    {"name": "commons-csv", "url": "https://github.com/apache/commons-csv", "language": "Java"},
    {"name": "dubbo", "url": "https://github.com/apache/dubbo", "language": "Java"},
    {"name": "mybatis-3", "url": "https://github.com/mybatis/mybatis-3", "language": "Java"},
    {"name": "rocketmq", "url": "https://github.com/apache/rocketmq", "language": "Java"},
    {"name": "guava", "url": "https://github.com/google/guava", "language": "Java"},
    {"name": "RxJava", "url": "https://github.com/ReactiveX/RxJava", "language": "Java"},
    {"name": "Activiti", "url": "https://github.com/Activiti/Activiti", "language": "Java"},
    {"name": "spring-security", "url": "https://github.com/spring-projects/spring-security", "language": "Java"},

    # JavaScript Projects (12)
    {"name": "react", "url": "https://github.com/facebook/react", "language": "Javascript"},
    {"name": "vue", "url": "https://github.com/vuejs/vue", "language": "Javascript"},
    {"name": "bootstrap", "url": "https://github.com/twbs/bootstrap", "language": "Javascript"},
    {"name": "node", "url": "https://github.com/nodejs/node", "language": "Javascript"},
    {"name": "axios", "url": "https://github.com/axios/axios", "language": "Javascript"},
    {"name": "typescript", "url": "https://github.com/microsoft/TypeScript", "language": "Javascript"},
    {"name": "deno", "url": "https://github.com/denoland/deno", "language": "Javascript"},
    {"name": "mermaid", "url": "https://github.com/mermaid-js/mermaid", "language": "Javascript"},
    {"name": "nest", "url": "https://github.com/nestjs/nest", "language": "Javascript"},
    {"name": "webpack", "url": "https://github.com/webpack/webpack", "language": "Javascript"},
    {"name": "express", "url": "https://github.com/expressjs/express", "language": "Javascript"},
    {"name": "Chart.js", "url": "https://github.com/chartjs/Chart.js", "language": "Javascript"},

    # C Projects (10)
    {"name": "git", "url": "https://github.com/git/git", "language": "C"},
    {"name": "mpv", "url": "https://github.com/mpv-player/mpv", "language": "C"},
    {"name": "FreeRTOS-Kernel", "url": "https://github.com/FreeRTOS/FreeRTOS-Kernel", "language": "C"},
    {"name": "ccache", "url": "https://github.com/ccache/ccache", "language": "C"},
    {"name": "msgpack-c", "url": "https://github.com/msgpack/msgpack-c", "language": "C"},
    {"name": "openvpn", "url": "https://github.com/OpenVPN/openvpn", "language": "C"},
    {"name": "distcc", "url": "https://github.com/distcc/distcc", "language": "C"},
    {"name": "xrdp", "url": "https://github.com/neutrinolabs/xrdp", "language": "C"},
    {"name": "libevent", "url": "https://github.com/libevent/libevent", "language": "C"},
    {"name": "json-c", "url": "https://github.com/json-c/json-c", "language": "C"},

    # C++ Projects (8)
    {"name": "tensorflow", "url": "https://github.com/tensorflow/tensorflow", "language": "C++"},
    {"name": "react-native", "url": "https://github.com/facebook/react-native", "language": "C++"},
    {"name": "opencv", "url": "https://github.com/opencv/opencv", "language": "C++"},
    {"name": "imgui_test_engine", "url": "https://github.com/ocornut/imgui_test_engine", "language": "C++"},
    {"name": "folly", "url": "https://github.com/facebook/folly", "language": "C++"},
    {"name": "xgboost", "url": "https://github.com/dmlc/xgboost", "language": "C++"},
    {"name": "webview", "url": "https://github.com/webview/webview", "language": "C++"},
    {"name": "json", "url": "https://github.com/nlohmann/json", "language": "C++"},
]


def find_test_directories(project_path, language):
    """Find test directories and files in a project."""
    test_info = {
        "test_directories": [],
        "test_files": [],
        "test_commands": []
    }

    # Common test directory patterns
    test_dir_patterns = ["test", "tests", "testing", "spec", "specs", "__tests__"]

    # Language-specific test file patterns
    test_file_patterns = {
        "Python": ["test_*.py", "*_test.py", "test*.py"],
        "Java": ["*Test.java", "*Tests.java", "Test*.java"],
        "Javascript": ["*.test.js", "*.spec.js", "*.test.ts", "*.spec.ts"],
        "C": ["test_*.c", "*_test.c", "test*.c"],
        "C++": ["test_*.cpp", "*_test.cpp", "test*.cpp", "*_test.cc", "test*.cc"]
    }

    # Language-specific build/test config files
    config_files = {
        "Python": ["pytest.ini", "setup.py", "pyproject.toml", "tox.ini", "setup.cfg"],
        "Java": ["pom.xml", "build.gradle", "build.xml"],
        "Javascript": ["package.json", "jest.config.js", "karma.conf.js"],
        "C": ["Makefile", "CMakeLists.txt", "configure.ac"],
        "C++": ["Makefile", "CMakeLists.txt", "meson.build"]
    }

    # Find test directories
    for pattern in test_dir_patterns:
        for root, dirs, files in os.walk(project_path):
            # Limit depth to avoid going too deep
            depth = root[len(str(project_path)):].count(os.sep)
            if depth > 3:
                continue

            for d in dirs:
                if pattern in d.lower():
                    test_dir = os.path.join(root, d)
                    test_info["test_directories"].append(test_dir)

    # Find config files
    patterns = config_files.get(language, [])
    for pattern in patterns:
        for root, dirs, files in os.walk(project_path):
            depth = root[len(str(project_path)):].count(os.sep)
            if depth > 2:
                continue
            for f in files:
                if f == pattern or f.endswith(pattern):
                    test_info["test_files"].append(os.path.join(root, f))

    return test_info


def clone_project(project, base_dir):
    """Clone a project repository."""
    project_name = project["name"]
    project_url = project["url"]
    language = project["language"]

    safe_name = project_name.lower().replace("-", "_").replace(".", "_")
    project_dir = base_dir / language / safe_name

    print(f"\n{'='*60}")
    print(f"Processing: {project_name} ({language})")
    print(f"URL: {project_url}")
    print(f"{'='*60}")

    # Skip if already exists
    if project_dir.exists():
        print(f"⚠️  Directory already exists: {project_dir}")
        print(f"Skipping clone...")
    else:
        print(f"📥 Cloning into: {project_dir}")
        project_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Clone with depth=1 to save space and time
            subprocess.run(
                ["git", "clone", "--depth", "1", project_url, str(project_dir)],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✅ Clone successful")
        except subprocess.CalledProcessError as e:
            print(f"❌ Clone failed: {e.stderr}")
            return None

    # Find test information
    print(f"🔍 Analyzing test structure...")
    test_info = find_test_directories(project_dir, language)

    # Create metadata
    metadata = {
        "project_name": project_name,
        "project_url": project_url,
        "language": language,
        "project_path": str(project_dir),
        "test_directories": test_info["test_directories"],
        "test_config_files": test_info["test_files"],
        "downloaded_at": datetime.now().isoformat(),
    }

    # Save metadata
    metadata_file = project_dir / "test_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(metadata, indent=2, fp=f)

    print(f"📊 Test directories found: {len(test_info['test_directories'])}")
    print(f"📊 Config files found: {len(test_info['test_files'])}")
    print(f"💾 Metadata saved to: {metadata_file}")

    return metadata


def main():
    """Main function to download all projects."""
    script_dir = Path(__file__).parent
    base_dir = script_dir / "projects"

    print("="*80)
    print("ExecutionAgent Test Projects Downloader")
    print("="*80)
    print(f"Total projects: {len(PROJECTS)}")
    print(f"Base directory: {base_dir}")
    print()

    # Group by language
    by_language = {}
    for p in PROJECTS:
        lang = p["language"]
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(p)

    print("Projects by language:")
    for lang, projs in sorted(by_language.items()):
        print(f"  {lang}: {len(projs)}")
    print()

    # Create base directory
    base_dir.mkdir(exist_ok=True)

    # Download all projects
    results = []
    for i, project in enumerate(PROJECTS, 1):
        print(f"\n[{i}/{len(PROJECTS)}]")
        metadata = clone_project(project, base_dir)
        if metadata:
            results.append(metadata)

    # Create summary
    summary = {
        "total_projects": len(PROJECTS),
        "successfully_downloaded": len(results),
        "by_language": {lang: len(projs) for lang, projs in by_language.items()},
        "projects": results,
        "generated_at": datetime.now().isoformat(),
    }

    summary_file = base_dir / "download_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, indent=2, fp=f)

    print("\n" + "="*80)
    print("Download Summary")
    print("="*80)
    print(f"Total projects: {len(PROJECTS)}")
    print(f"Successfully downloaded: {len(results)}")
    print(f"Summary saved to: {summary_file}")
    print("="*80)


if __name__ == "__main__":
    main()
