import json
import argparse
import sys

def calculate_version(node):
    """
    Calculate the combination number for a version node.
    It equals the product of the combination numbers of all its child package nodes.
    If the node is empty (i.e., a leaf node), its combination value is 1.
    """
    if not node:
        return 1
        
    result = 1
    for pkg_name, pkg_node in node.items():
        result *= calculate_package(pkg_node)
    return result

def calculate_package(node):
    """
    Calculate the combination number for a package node.
    It equals the sum of the combination numbers of all its child version nodes.
    """
    if not node:
        return 0
        
    result = 0
    for ver_name, ver_node in node.items():
        result += calculate_version(ver_node)
    return result

def main():
    # Initialize the argument parser
    parser = argparse.ArgumentParser(description="Calculate total combinations from a compatibility JSON tree.")
    
    # Add required positional arguments
    parser.add_argument("input_file", help="Path to the input JSON file (e.g., CVE-2024-0520-compatibility.json)")
    parser.add_argument("output_file", help="Path to the output JSON file (e.g., CVE-2024-0520-statistics.json)")
    
    args = parser.parse_args()
    
    try:
        # Load the compatibility JSON data
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The input file '{args.input_file}' was not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: The input file '{args.input_file}' is not a valid JSON.")
        sys.exit(1)
        
    # The root of the JSON acts as a top-level version node containing packages
    total_combinations = calculate_version(data)
    
    # Prepare the statistics data to be saved
    statistics_data = {
        "total_combinations": total_combinations
    }
    
    try:
        # Save the result to the output JSON file
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(statistics_data, f, indent=4)
            
        print(f"{'='*50}")
        print(f"✅ Calculation complete!")
        print(f"🔢 Total combinations: {total_combinations}")
        print(f"📁 Results successfully saved to: {args.output_file}")
        print(f"{'='*50}")
    except Exception as e:
        print(f"Error: Failed to write to the output file. Details: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()