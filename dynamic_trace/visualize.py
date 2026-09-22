import json
import uuid
import argparse
import os
import re
from pyvis.network import Network

def add_nodes_edges(data_node, net, parent_id=None):
    """Recursively add nodes and edges to the network graph."""
    if isinstance(data_node, dict):
        for key, value in data_node.items():
            # Generate a unique ID for each node to prevent merging identical version numbers across different branches
            node_id = str(uuid.uuid4()) 
            
            # Differentiate colors for package names and version numbers (based on the presence of digits)
            color = "#97C2FC" if any(char.isdigit() for char in str(key)) else "#FFB347"
            
            # Add the current node
            net.add_node(node_id, label=str(key), title=str(key), color=color, shape="box")
            
            # Connect to the parent node if it exists
            if parent_id:
                net.add_edge(parent_id, node_id)
                
            # Recursively process child nodes
            add_nodes_edges(value, net, node_id)

def main():
    # Initialize the argument parser
    parser = argparse.ArgumentParser(description="Generate an interactive dependency tree from a JSON file.")
    
    # Add required positional arguments
    parser.add_argument("input_file", help="Path to the input JSON file (e.g., /path/to/CVE-2024-0520-compatibility.json)")
    parser.add_argument("output_file", help="Path to the output HTML file (e.g., dependency_tree.html)")
    
    # Parse the arguments from the command line
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file
    
    # Initialize the network graph with directed edges and a hierarchical layout
    net = Network(height="1000px", width="100%", directed=True)
    
    # Force hierarchical tree layout (Left to Right) and DISABLE physics for fast rendering
    net.set_options("""
    var options = {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "LR",
          "sortMethod": "directed",
          "levelSeparation": 250,
          "nodeSpacing": 80
        }
      },
      "physics": {
        "enabled": false
      },
      "edges": {
        "smooth": {
          "type": "cubicBezier",
          "forceDirection": "horizontal",
          "roundness": 0.4
        }
      }
    }
    """)

    try:
        # Load the JSON data from the provided input file path
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: The file '{input_file}' is not a valid JSON file.")
        return

    # Extract CVE ID from the filename using regular expressions
    base_name = os.path.basename(input_file)
    # This regex looks for 'CVE-' followed by 4 digits, a hyphen, and at least 1 digit (e.g., CVE-2024-0520)
    match = re.search(r'CVE-\d{4}-\d+', base_name, re.IGNORECASE)
    
    if match:
        root_label = match.group(0).upper()
    else:
        # Fallback just in case the filename doesn't contain a standard CVE format
        root_label = base_name.split('.')[0].replace('-compatibility', '')

    # Create the root node using the extracted CVE ID as the label
    root_id = "ROOT"
    net.add_node(root_id, label=root_label, color="#FF69B4", shape="ellipse")
    
    # Build the tree starting from the root
    add_nodes_edges(data, net, root_id)

    # Output the result to the provided output file path
    net.save_graph(output_file)
    print(f"Visualization complete! Please open '{output_file}' in a web browser to view the interactive graph.")

if __name__ == "__main__":
    main()