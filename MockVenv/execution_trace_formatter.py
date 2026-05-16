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
                                       execution_trace_file=None, project_path=None,
                                       requirements_file=None, validation_stats=None):
    """
    Generate an enhanced resolution report with detailed reasoning,
    release dates, and usage frequency ranking.

    Args:
        resolved_packages: Dict {package_name: {versions: [...], reasoning: {...}}}
        api_calls_file: Path to .api_calls.json
        execution_trace_file: Optional path to .execution_trace.json
        project_path: Optional project path for relative paths
        requirements_file: Optional path to requirements.txt for version comparison
        validation_stats: Optional dict with validation statistics from script_based_validator

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

    # Section 2.5: Validation Statistics Summary (NEW)
    if validation_stats:
        output.append("=" * 80)
        output.append("📊 VERSION VALIDATION STATISTICS")
        output.append("=" * 80)
        output.append("")
        output.append("This section shows the validation pipeline statistics:")
        output.append("")

        total_pypi = validation_stats.get('total_pypi_versions', 0)
        total_installable = validation_stats.get('total_installable_versions', 0)
        total_script_passed = validation_stats.get('total_script_passed_versions', 0)

        output.append(f"   Step 1 - PyPI Fetch:            {total_pypi:5d} versions")
        output.append(f"   Step 2 - Installation Test:    {total_installable:5d} versions (uv pip install)")
        output.append(f"   Step 3 - Script Validation:    {total_script_passed:5d} versions (python script test)")
        output.append("")

        if total_pypi > 0:
            install_rate = (total_installable / total_pypi) * 100
            output.append(f"   Installation Success Rate:     {install_rate:.1f}%")

        if total_installable > 0:
            script_rate = (total_script_passed / total_installable) * 100
            output.append(f"   Script Test Success Rate:      {script_rate:.1f}%")

        output.append("")

        # Check for requirements.txt version failures
        req_failures = validation_stats.get('requirements_version_failures', [])
        if req_failures:
            output.append("   ⚠️  WARNING: Requirements.txt Version Failures Detected!")
            output.append("")
            output.append("   The following packages have requirements.txt versions that FAILED")
            output.append("   the python script validation. This indicates potential issues with")
            output.append("   the test scripts or API breaking changes:")
            output.append("")
            for pkg_name, req_version, error_reason in req_failures:
                output.append(f"      ❌ {pkg_name} (version {req_version})")
                if error_reason:
                    output.append(f"         Reason: {error_reason}")
            output.append("")
            output.append("   💡 Recommendation: Review the test scripts for these packages")
            output.append("      or verify the API compatibility of the specified versions.")

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

    # Load requirements.txt versions for comparison
    requirements_versions = {}
    if requirements_file and os.path.exists(requirements_file):
        try:
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '==' in line:
                        pkg_name, version = line.split('==', 1)
                        pkg_name = pkg_name.strip()
                        version = version.strip()
                        # Store both normalized and original names
                        normalized = pkg_name.lower().replace('_', '-')
                        requirements_versions[normalized] = version
                        requirements_versions[pkg_name] = version
        except Exception as e:
            pass

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
        validation_status = package_data.get('validation_status', 'unknown')

        output.append("-" * 80)
        output.append(f"📦 Package: {package}")
        output.append("-" * 80)

        # Usage frequency
        if package in usage_freq:
            output.append(f"   Usage: {usage_freq[package]} API calls")
        output.append("")

        # Requirements.txt version (NEW)
        normalized_pkg = package.lower().replace('_', '-')
        req_version = requirements_versions.get(normalized_pkg) or requirements_versions.get(package)
        if req_version:
            output.append(f"   📋 Requirements.txt version: {req_version}")
            # Check if requirements version passed validation
            if versions and req_version not in versions:
                output.append(f"      ⚠️  WARNING: This version is NOT in the validated versions list!")
                output.append(f"      This indicates the requirements.txt version failed script validation.")
            output.append("")

        # APIs used
        if api_usage:
            output.append("   APIs Used (that influenced version inference):")
            for api in api_usage[:10]:  # Show first 10
                output.append(f"      • {api}")
            if len(api_usage) > 10:
                output.append(f"      ... and {len(api_usage) - 10} more")
            output.append("")

        # Version resolution reasoning (MODIFIED - remove PENDING_VALIDATION)
        output.append("   Version Resolution:")
        if reasoning:
            confidence = reasoning.get('confidence', 'unknown')
            reasoning_text = reasoning.get('reasoning', '')

            # Skip the meaningless PENDING_VALIDATION section
            if confidence.lower() != 'pending_validation':
                output.append(f"      Confidence: {confidence.upper()}")

                if reasoning.get('detected_patterns'):
                    output.append("      Detected Patterns:")
                    for pattern in reasoning['detected_patterns']:
                        output.append(f"         - {pattern}")

                if reasoning_text and 'will be validated by script-based testing' not in reasoning_text:
                    output.append(f"      Reasoning: {reasoning_text}")

                if reasoning.get('version_constraints'):
                    output.append(f"      Constraint: {reasoning['version_constraints']}")

        # Add validation statistics for this package (NEW)
        if validation_stats and 'packages' in validation_stats:
            pkg_stats = validation_stats['packages'].get(package, {})
            if pkg_stats:
                pypi_count = pkg_stats.get('pypi_versions', 0)
                install_count = pkg_stats.get('installable_versions', 0)
                script_count = pkg_stats.get('script_passed_versions', 0)

                output.append("")
                output.append("   Validation Pipeline:")
                output.append(f"      PyPI versions fetched:          {pypi_count}")
                output.append(f"      Installable (uv pip install):  {install_count}")
                output.append(f"      Passed script validation:       {script_count}")

                if pypi_count > 0 and install_count > 0 and script_count > 0:
                    output.append(f"      Installation success rate:      {(install_count/pypi_count)*100:.1f}%")
                    output.append(f"      Script validation rate:         {(script_count/install_count)*100:.1f}%")

                # NEW: Check if requirements.txt version is in passed script versions
                if req_version and script_count > 0 and versions:
                    if req_version not in versions:
                        output.append("")
                        output.append(f"      ⚠️  WARNING: Requirements.txt version ({req_version}) is NOT in")
                        output.append(f"          the validated versions list!")
                        output.append(f"          This indicates the requirements.txt version failed script validation.")
                elif req_version and script_count == 0:
                    output.append("")
                    output.append(f"      ⚠️  WARNING: No versions passed script validation!")
                    output.append(f"          Requirements.txt version ({req_version}) also failed validation.")
                    output.append(f"          Using requirements.txt version as fallback (not validated).")

        output.append("")

        # Compatible versions with release dates
        # Add requirements.txt version if it's not in the validated list
        versions_to_display = list(versions) if versions else []
        if req_version and req_version not in versions_to_display:
            # Add requirements.txt version at the beginning
            versions_to_display.insert(0, req_version)

        if versions_to_display:
            # Sort versions by release date (newest first)
            def get_sort_key(v):
                date_str = release_dates.get(v, None)
                if date_str and date_str != "unknown":
                    try:
                        return datetime.strptime(date_str, "%Y-%m-%d")
                    except:
                        pass
                # If no valid date, put at the end
                return datetime(1970, 1, 1)

            versions_to_display.sort(key=get_sort_key, reverse=True)

            output.append(f"   Compatible Versions: {len(versions_to_display)} found")
            output.append("")
            output.append("      Version          Release Date      Age")
            output.append("      " + "-" * 50)

            for version in versions_to_display:  # Show ALL versions
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

                # Mark requirements.txt version if it's not in the validated list
                marker = ""
                if version == req_version and version not in versions:
                    marker = " (⚠️ from requirements.txt - NOT validated)"

                output.append(f"      {version:16s} {release_date:16s}  {age}{marker}")
        else:
            output.append("   ⚠️ No compatible versions found")

        output.append("")

    output.append("=" * 80)
    output.append(f"✅ Total packages analyzed: {len(resolved_packages)}")
    output.append("=" * 80)

    return "\n".join(output)


def save_enhanced_report(resolved_packages, api_calls_file, output_file,
                         execution_trace_file=None, project_path=None,
                         requirements_file=None, validation_stats=None):
    """
    Generate and save enhanced resolution report to a file.

    Args:
        resolved_packages: Dict with package resolution data
        api_calls_file: Path to .api_calls.json
        output_file: Path to save the report
        execution_trace_file: Optional path to .execution_trace.json
        project_path: Optional project path
        requirements_file: Optional path to requirements.txt
        validation_stats: Optional dict with validation statistics
    """
    report = format_enhanced_resolution_report(
        resolved_packages, api_calls_file, execution_trace_file, project_path,
        requirements_file, validation_stats
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Enhanced resolution report saved to: {output_file}")
