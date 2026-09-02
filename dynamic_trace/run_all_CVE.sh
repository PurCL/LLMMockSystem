#!/bin/bash

# 定义 CVE 列表
CVES=(
    "CVE-2026-1462"
    "CVE-2026-27628"
    "CVE-2026-33992"
    "CVE-2026-38743"
    "CVE-2026-42874"
    "CVE-2026-4539
    CVE-2026-2033"
    "CVE-2026-27809"
    "CVE-2026-34531"
    "CVE-2026-40192"
    "CVE-2026-44307
    CVE-2026-26007"
    "CVE-2026-27826"
    "CVE-2026-34730"
    "CVE-2026-40690"
    "CVE-2026-44405
    CVE-2026-26013"
    "CVE-2026-32711"
    "CVE-2026-34839"
    "CVE-2026-42175"
    "CVE-2026-44513
    CVE-2026-27448"
    "CVE-2026-33054"
    "CVE-2026-35459"
    "CVE-2026-42304"
    "CVE-2026-44827"
)

# 遍历列表并执行命令
for CVE in "${CVES[@]}"; do
    echo "========================================"
    echo "正在执行: $CVE"
    echo "========================================"
    
    python3 run_recursive_api_analysis.py ../cve/2026/library/$CVE/run_exploit.sh --vulnerable-file ../cve/2026/library/$CVE/vulnerable_versions.json --CVE $CVE --requirements ../cve/2026/library/$CVE/requirements.txt
done

echo "所有 CVE 执行完毕。"