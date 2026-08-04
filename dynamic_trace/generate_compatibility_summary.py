#!/usr/bin/env python3
"""
Generate a summarized markdown file from compatibility.json
Similar to tree_output.md format
"""
import json
from collections import defaultdict

def load_compatibility_data(json_path):
    """Load the compatibility JSON file"""
    with open(json_path, 'r') as f:
        return json.load(f)

def summarize_versions(versions):
    """Summarize version range"""
    version_list = sorted(versions)
    if len(version_list) == 0:
        return "No versions"
    elif len(version_list) == 1:
        return version_list[0]
    else:
        return f"{version_list[0]} to {version_list[-1]}"

def get_dependency_versions(package_data):
    """Get all unique dependencies and their version ranges across all package versions"""
    dep_versions = defaultdict(set)

    for version, deps in package_data.items():
        for dep_name, dep_details in deps.items():
            if isinstance(dep_details, dict):
                if "ALL" in dep_details:
                    dep_versions[dep_name].add("ALL")
                else:
                    for ver in dep_details.keys():
                        dep_versions[dep_name].add(ver)

    return dep_versions

def generate_markdown(data):
    """Generate markdown content from compatibility data"""
    lines = []

    # Header
    lines.append("# Package Compatibility Summary\n")
    lines.append("*Generated from compatibility.json*\n")
    lines.append("---\n")

    # For each main package
    for package_name, package_versions in data.items():
        lines.append(f"\n## {package_name}")

        # Version range
        version_range = summarize_versions(list(package_versions.keys()))
        lines.append(f"**Versions:** {version_range} ({len(package_versions)} versions)")

        # Get all dependencies
        dep_versions = get_dependency_versions(package_versions)

        if not dep_versions:
            lines.append("\n*No dependencies found*\n")
            continue

        lines.append(f"\n**Dependencies:** {len(dep_versions)} unique dependencies\n")

        # List dependencies with their version info
        lines.append("### Dependency Details\n")

        # Sort dependencies by name
        sorted_deps = sorted(dep_versions.items())

        # Group dependencies
        all_deps = []
        versioned_deps = []

        for dep_name, versions in sorted_deps:
            if "ALL" in versions or len(versions) == 0:
                all_deps.append(dep_name)
            else:
                versioned_deps.append((dep_name, versions))

        # Show major dependencies first (those with specific versions)
        if versioned_deps:
            lines.append("**Major Dependencies:**\n")
            for dep_name, versions in versioned_deps[:10]:  # Show top 10
                ver_range = summarize_versions(sorted(versions))
                lines.append(f"- `{dep_name}`: {ver_range}")

            if len(versioned_deps) > 10:
                lines.append(f"- *... and {len(versioned_deps) - 10} more versioned dependencies*")

        lines.append("")

        # Show ALL dependencies count
        if all_deps:
            lines.append(f"**Common Dependencies (ALL versions):** {len(all_deps)}")
            # Show first 20
            if len(all_deps) <= 20:
                lines.append(f"\n{', '.join(f'`{d}`' for d in all_deps[:20])}")
            else:
                lines.append(f"\n{', '.join(f'`{d}`' for d in all_deps[:20])}, *... and {len(all_deps) - 20} more*")

        lines.append("\n---")

    # Summary at the end
    lines.append("\n## Summary Statistics\n")
    total_packages = len(data)
    total_versions = sum(len(versions) for versions in data.values())

    lines.append(f"- **Total Main Packages:** {total_packages}")
    lines.append(f"- **Total Package Versions:** {total_versions}")

    for pkg_name, pkg_data in data.items():
        dep_count = len(get_dependency_versions(pkg_data))
        lines.append(f"- **{pkg_name}:** {len(pkg_data)} versions, {dep_count} dependencies")

    return "\n".join(lines)

def generate_mermaid_mindmap(data):
    """Generate a mermaid mindmap similar to tree_output.md"""
    lines = []
    lines.append("```mermaid")
    lines.append("mindmap")
    lines.append("  root((Compatibility Tree))")

    for package_name, package_versions in data.items():
        lines.append(f"    {package_name}")

        # Version info
        version_range = summarize_versions(list(package_versions.keys()))
        lines.append(f"      (Versions: {version_range})")
        lines.append(f"      ({len(package_versions)} versions total)")

        # Get dependencies
        dep_versions = get_dependency_versions(package_versions)

        if dep_versions:
            lines.append(f"      ({len(dep_versions)} dependencies)")

            # Show sample dependencies
            all_deps = [name for name, vers in dep_versions.items() if "ALL" in vers]
            versioned_deps = [(name, vers) for name, vers in dep_versions.items() if "ALL" not in vers]

            # Show a few major dependencies
            for dep_name, versions in sorted(versioned_deps)[:3]:
                lines.append(f"      {dep_name}")
                ver_range = summarize_versions(sorted(versions))
                lines.append(f"        ({ver_range})")

            if len(all_deps) > 0:
                lines.append(f"      (Common modules: {', '.join(all_deps[:5])})")
                if len(all_deps) > 5:
                    lines.append(f"        [+{len(all_deps) - 5} more]")

    lines.append("```")
    return "\n".join(lines)

def main():
    input_file = "/home/jian1000/data3/LLMMockSystem/pyright/compatibility.json"
    output_file = "/home/jian1000/data3/LLMMockSystem/pyright/compatibility_summary.md"

    print(f"Loading data from {input_file}...")
    data = load_compatibility_data(input_file)

    print("Generating markdown content...")

    # Generate both formats
    mindmap_content = generate_mermaid_mindmap(data)
    markdown_content = generate_markdown(data)

    # Combine them
    full_content = f"{mindmap_content}\n\n{markdown_content}"

    print(f"Writing to {output_file}...")
    with open(output_file, 'w') as f:
        f.write(full_content)

    print(f"✓ Successfully generated {output_file}")
    print(f"  - Total packages: {len(data)}")
    print(f"  - Total versions: {sum(len(v) for v in data.values())}")

if __name__ == "__main__":
    main()
