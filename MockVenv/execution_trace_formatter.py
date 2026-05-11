#!/usr/bin/env python3
"""
Execution Trace Formatter

This module provides user-friendly formatting for execution traces and dependency resolution results.
It creates detailed reports showing:
1. Program execution trace (which files/lines executed which APIs)
2. Detailed package version reasoning (which APIs led to which version inference)
3. Release dates for each version
4. Package usage frequency ranking
"""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime


def format_execution_trace(trace_file, project_path=None):
    """
    Format execution trace from .execution_trace.json into a user-friendly report.

    Args:
        trace_file: Path to .execution_trace.json file
        project_path: Optional project path to make file paths relative

    Returns:
        Formatted string showing the execution flow
    """
    if not os.path.exists(trace_file):
        return "❌ Execution trace file not found. Make sure the program ran with the enhanced hook."

    with open(trace_file, 'r', encoding='utf-8') as f:
        trace_data = json.load(f)

    if not trace_data:
        return "⚠️ No execution trace data found."

    # Build execution flow
    output = []
    output.append("=" * 80)
    output.append("📋 PROGRAM EXECUTION TRACE")
    output.append("=" * 80)
    output.append("")
    output.append("This trace shows the sequential execution of your program,")
    output.append("tracking which files and lines called which library APIs.")
    output.append("")

    # Group by user file for better readability
    current_user_file = None
    api_counter = 1

    for entry in trace_data:
        api = entry.get("api", "")
        caller = entry.get("caller", {})
        params = entry.get("params", "")

        user_file = caller.get("user_file")
        user_line = caller.get("user_line")
        user_function = caller.get("user_function")

        # Make path relative if project_path is provided
        if user_file and project_path:
            try:
                user_file = os.path.relpath(user_file, project_path)
            except:
                pass

        # Print file header if it changed
        if user_file and user_file != current_user_file:
            current_user_file = user_file
            output.append("")
            output.append("-" * 80)
            output.append(f"📄 File: {user_file}")
            output.append("-" * 80)

        # Format API call
        if user_line and user_function:
            output.append(f"  [{api_counter}] Line {user_line} in {user_function}()")
        else:
            output.append(f"  [{api_counter}] (location unknown)")

        output.append(f"      ↳ API: {api}")
        if params:
            # Truncate long params
            params_display = params if len(params) < 100 else params[:100] + "..."
            output.append(f"      ↳ Params: {params_display}")

        output.append("")
        api_counter += 1

    output.append("=" * 80)
    output.append(f"✅ Total API calls traced: {len(trace_data)}")
    output.append("=" * 80)

    return "\n".join(output)


def analyze_package_usage_frequency(api_calls_file):
    """
    Analyze API usage frequency per package.

    Args:
        api_calls_file: Path to .api_calls.json file

    Returns:
        Dict {package_name: call_count}
    """
    if not os.path.exists(api_calls_file):
        return {}

    with open(api_calls_file, 'r', encoding='utf-8') as f:
        api_calls = f.readlines()

    package_counter = Counter()

    for line in api_calls:
        line = line.strip()
        if line and '.' in line:
            package = line.split('.')[0]
            package_counter[package] += 1

    return dict(package_counter)


def format_enhanced_resolution_report(resolved_packages, api_calls_file,
                                       execution_trace_file=None, project_path=None):
    """
    Generate an enhanced resolution report with detailed reasoning,
    release dates, and usage frequency ranking.

    Args:
        resolved_packages: Dict {package_name: {versions: [...], reasoning: {...}}}
        api_calls_file: Path to .api_calls.json
        execution_trace_file: Optional path to .execution_trace.json
        project_path: Optional project path for relative paths

    Returns:
        Formatted string with comprehensive report
    """
    output = []

    # Section 1: Execution Trace
    if execution_trace_file and os.path.exists(execution_trace_file):
        output.append(format_execution_trace(execution_trace_file, project_path))
        output.append("\n" * 2)

    # Section 2: Package Usage Frequency
    output.append("=" * 80)
    output.append("📊 PACKAGE USAGE FREQUENCY RANKING")
    output.append("=" * 80)
    output.append("")

    usage_freq = analyze_package_usage_frequency(api_calls_file)
    if usage_freq:
        # Sort by frequency (descending)
        sorted_packages = sorted(usage_freq.items(), key=lambda x: x[1], reverse=True)

        output.append("Packages ranked by number of API calls during execution:")
        output.append("")
        for rank, (package, count) in enumerate(sorted_packages, 1):
            bar_length = min(50, count)  # Visual bar
            bar = "█" * bar_length
            output.append(f"  {rank:2d}. {package:20s} │ {bar} {count} calls")

        output.append("")
        output.append(f"✅ Total packages used: {len(sorted_packages)}")
    else:
        output.append("⚠️ No package usage data found.")

    output.append("=" * 80)
    output.append("\n" * 2)

    # Section 3: Detailed Package Version Resolution
    output.append("=" * 80)
    output.append("📦 DETAILED PACKAGE VERSION RESOLUTION")
    output.append("=" * 80)
    output.append("")

    if not resolved_packages:
        output.append("⚠️ No packages resolved.")
        return "\n".join(output)

    # Sort packages by usage frequency for display
    package_order = [pkg for pkg, _ in sorted(
        usage_freq.items(), key=lambda x: x[1], reverse=True
    )] if usage_freq else list(resolved_packages.keys())

    # Add packages not in usage data at the end
    for pkg in resolved_packages:
        if pkg not in package_order:
            package_order.append(pkg)

    for package in package_order:
        if package not in resolved_packages:
            continue

        package_data = resolved_packages[package]
        versions = package_data.get('versions', [])
        reasoning = package_data.get('reasoning', {})
        api_usage = package_data.get('api_usage', [])
        release_dates = package_data.get('release_dates', {})

        output.append("-" * 80)
        output.append(f"📦 Package: {package}")
        output.append("-" * 80)

        # Usage frequency
        if package in usage_freq:
            output.append(f"   Usage: {usage_freq[package]} API calls")
        output.append("")

        # APIs used
        if api_usage:
            output.append("   APIs Used (that influenced version inference):")
            for api in api_usage[:10]:  # Show first 10
                output.append(f"      • {api}")
            if len(api_usage) > 10:
                output.append(f"      ... and {len(api_usage) - 10} more")
            output.append("")

        # Version resolution reasoning
        output.append("   Version Resolution:")
        if reasoning:
            confidence = reasoning.get('confidence', 'unknown')
            output.append(f"      Confidence: {confidence.upper()}")

            if reasoning.get('detected_patterns'):
                output.append("      Detected Patterns:")
                for pattern in reasoning['detected_patterns']:
                    output.append(f"         - {pattern}")

            if reasoning.get('reasoning'):
                output.append(f"      Reasoning: {reasoning['reasoning']}")

            if reasoning.get('version_constraints'):
                output.append(f"      Constraint: {reasoning['version_constraints']}")
        output.append("")

        # Compatible versions with release dates
        if versions:
            output.append(f"   Compatible Versions: {len(versions)} found")
            output.append("")
            output.append("      Version          Release Date      Age")
            output.append("      " + "-" * 50)

            for version in versions[:20]:  # Show first 20
                release_date = release_dates.get(version, "unknown")
                # Handle None or empty release_date
                if release_date is None:
                    release_date = "unknown"

                age = ""
                if release_date and release_date != "unknown":
                    try:
                        rel_date = datetime.strptime(release_date, "%Y-%m-%d")
                        age_days = (datetime.now() - rel_date).days
                        if age_days < 365:
                            age = f"({age_days} days ago)"
                        else:
                            age_years = age_days / 365
                            age = f"({age_years:.1f} years ago)"
                    except:
                        pass

                output.append(f"      {version:16s} {release_date:16s}  {age}")

            if len(versions) > 20:
                output.append(f"      ... and {len(versions) - 20} more versions")
        else:
            output.append("   ⚠️ No compatible versions found")

        output.append("")

    output.append("=" * 80)
    output.append(f"✅ Total packages analyzed: {len(resolved_packages)}")
    output.append("=" * 80)

    return "\n".join(output)


def save_enhanced_report(resolved_packages, api_calls_file, output_file,
                         execution_trace_file=None, project_path=None):
    """
    Generate and save enhanced resolution report to a file.

    Args:
        resolved_packages: Dict with package resolution data
        api_calls_file: Path to .api_calls.json
        output_file: Path to save the report
        execution_trace_file: Optional path to .execution_trace.json
        project_path: Optional project path
    """
    report = format_enhanced_resolution_report(
        resolved_packages, api_calls_file, execution_trace_file, project_path
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Enhanced resolution report saved to: {output_file}")
