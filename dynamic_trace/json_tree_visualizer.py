#!/usr/bin/env python3
"""
JSON Tree Visualizer Tool
Display JSON data in Mermaid mindmap format, with CVE as root node
"""

import json
import sys
from typing import Any, Dict, List


class TreeVisualizer:
    """Tree visualization class for Mermaid mindmap format"""

    def __init__(self, root_name: str = "CVE"):
        """
        Initialize tree visualizer

        Args:
            root_name: Root node name, default is "CVE"
        """
        self.root_name = root_name

    def load_json(self, file_path: str) -> Dict:
        """
        Load JSON file

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found {file_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: JSON parsing failed - {e}")
            sys.exit(1)

    def _build_mindmap_lines(self, data: Any, indent_level: int = 1) -> List[str]:
        """
        Recursively build Mermaid mindmap structure lines

        Args:
            data: Data to display
            indent_level: Current indentation level (number of spaces = indent_level * 2)

        Returns:
            List of mindmap structure text lines
        """
        lines = []
        indent = "  " * indent_level

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    # Dictionary node
                    lines.append(f"{indent}{key}")
                    lines.extend(self._build_mindmap_lines(value, indent_level + 1))
                elif isinstance(value, list):
                    # List node
                    lines.append(f"{indent}{key}")
                    lines.extend(self._build_mindmap_lines(value, indent_level + 1))
                else:
                    # Leaf node with value
                    lines.append(f"{indent}{key}")
                    if value is not None and value != "":
                        lines.append(f"{indent}  ({value})")

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Dictionary in list
                    lines.extend(self._build_mindmap_lines(item, indent_level))
                elif isinstance(item, list):
                    # Nested list
                    lines.extend(self._build_mindmap_lines(item, indent_level))
                else:
                    # Primitive value in list
                    if item is not None and item != "":
                        lines.append(f"{indent}({item})")

        return lines

    def visualize(self, data: Dict) -> str:
        """
        Visualize JSON data as Mermaid mindmap

        Args:
            data: JSON data

        Returns:
            Mermaid mindmap string representation
        """
        lines = ["```mermaid", "mindmap", f"  root(({self.root_name}))"]
        lines.extend(self._build_mindmap_lines(data, indent_level=2))
        lines.append("```")
        return '\n'.join(lines)

    def save_tree(self, tree_text: str, output_path: str):
        """
        Save mindmap to file

        Args:
            tree_text: Mindmap text
            output_path: Output file path
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(tree_text)
            print(f"Mindmap saved to: {output_path}")
        except Exception as e:
            print(f"Error: Failed to save file - {e}")
            sys.exit(1)


def main():
    """Main function"""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python json_tree_visualizer.py <input_json_file> [output_file]")
        print("Example: python json_tree_visualizer.py output.json tree_output.md")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Create visualizer
    visualizer = TreeVisualizer(root_name="CVE")

    # Load JSON data
    print(f"Reading file: {input_file}")
    data = visualizer.load_json(input_file)

    # Generate mindmap
    print("Generating Mermaid mindmap...")
    tree_text = visualizer.visualize(data)

    # Output result
    if output_file:
        visualizer.save_tree(tree_text, output_file)
    else:
        print("\n" + "="*50)
        print("Mindmap Result:")
        print("="*50 + "\n")
        print(tree_text)


if __name__ == "__main__":
    main()
