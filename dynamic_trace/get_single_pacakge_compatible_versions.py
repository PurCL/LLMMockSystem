#!/usr/bin/env python3
"""
提取JSON文件中compatible字段的所有version，用空格隔开输出
"""
import json
import sys


def extract_compatible_versions(json_file_path):
    """
    从JSON文件中提取所有compatible的version

    Args:
        json_file_path: JSON文件路径

    Returns:
        用空格隔开的所有version字符串
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 获取compatible列表
        compatible = data.get('compatible', [])

        # 提取所有version
        versions = [item['version'] for item in compatible if 'version' in item]

        # 用空格隔开输出
        return ' '.join(versions)

    except FileNotFoundError:
        print(f"错误: 文件 '{json_file_path}' 不存在", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("用法: python extract_compatible_versions.py <json文件路径>")
        print("示例: python extract_compatible_versions.py /home/jian1000/data3/LLMMockSystem/pyright/CVE-2026-26007-api_log/cryptography_version_compatibility.json")
        sys.exit(1)

    json_file_path = sys.argv[1]
    versions = extract_compatible_versions(json_file_path)
    print(versions)


if __name__ == '__main__':
    main()
