#!/bin/bash
# ExecutionAgent 测试项目快速参考脚本

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "════════════════════════════════════════════════════════════════"
echo "  ExecutionAgent 测试项目快速参考"
echo "════════════════════════════════════════════════════════════════"
echo ""

# 统计信息
total_projects=$(find "$PROJECT_DIR/projects" -name "test_metadata.json" | wc -l)
echo "📊 总项目数: $total_projects"
echo ""

# 按语言统计
echo "📋 按语言分类:"
for lang_dir in "$PROJECT_DIR/projects"/*; do
    if [ -d "$lang_dir" ]; then
        lang=$(basename "$lang_dir")
        count=$(find "$lang_dir" -maxdepth 2 -name "test_metadata.json" | wc -l)
        echo "  - $lang: $count 个项目"
    fi
done
echo ""

# 显示每个项目的简要信息
echo "════════════════════════════════════════════════════════════════"
echo "  项目列表"
echo "════════════════════════════════════════════════════════════════"

for lang_dir in "$PROJECT_DIR/projects"/*; do
    if [ -d "$lang_dir" ]; then
        lang=$(basename "$lang_dir")
        echo ""
        echo "[$lang]"
        echo "----------------------------------------"

        for project_dir in "$lang_dir"/*; do
            if [ -d "$project_dir" ]; then
                project_name=$(basename "$project_dir")
                metadata_file="$project_dir/test_metadata.json"

                if [ -f "$metadata_file" ]; then
                    # 提取信息
                    url=$(grep -o '"project_url": "[^"]*"' "$metadata_file" | cut -d'"' -f4)
                    test_dir_count=$(grep -o '"test_directories": \[' "$metadata_file" -A 1000 | grep -o '"/[^"]*"' | wc -l)
                    config_count=$(grep -o '"test_config_files": \[' "$metadata_file" -A 100 | grep -o '"/[^"]*"' | wc -l)

                    printf "  %-25s | 测试目录: %3d | 配置文件: %2d\n" "$project_name" "$test_dir_count" "$config_count"
                fi
            fi
        done
    fi
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  常用命令"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "查看特定项目的测试元数据:"
echo "  cat projects/Python/pandas/test_metadata.json | python3 -m json.tool"
echo ""
echo "列出项目的测试目录:"
echo "  cat projects/Python/pandas/test_metadata.json | grep -A 50 test_directories"
echo ""
echo "查看项目源代码:"
echo "  cd projects/Python/pandas"
echo ""
echo "使用 ExecutionAgent 运行测试:"
echo "  cd ../ExecutionAgent"
echo "  python3 launcher.py --run pandas --verbose"
echo ""
echo "════════════════════════════════════════════════════════════════"
