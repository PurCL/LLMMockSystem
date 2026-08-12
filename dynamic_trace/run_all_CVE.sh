#!/bin/bash

# 定义 CVE 列表
CVES=(
    "CVE-2026-40192"
    "CVE-2026-40690"
    "CVE-2026-42175"
    "CVE-2026-42304"
    "CVE-2026-42874"
    "CVE-2026-44307"
    "CVE-2026-44364"
    "CVE-2026-44405"
    "CVE-2026-44513"
    "CVE-2026-44827"
    "CVE-2026-4539"
)

# 遍历列表并执行命令
for CVE in "${CVES[@]}"; do
    echo "========================================"
    echo "正在执行: $CVE"
    echo "========================================"
    
    python3 run_recursive_api_analysis.py "../cve/2026/library/$CVE"/run_exploit.sh --vulnerable-file "../cve/2026/library/$CVE/vulnerable_versions.json" --CVE "$CVE"
done

echo "所有 CVE 执行完毕。"