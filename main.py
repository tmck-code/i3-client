#!/usr/bin/env python3

from __future__ import annotations
from argparse import ArgumentParser
from dataclasses import dataclass, field
from itertools import chain
import json
from typing import Optional, List, Dict, Any
import subprocess
from typing import Iterable

from pprint_ndjson import pp

from i3_client.client import I3Node, I3Workspace, I3Output, I3Container, get_i3_tree, load_i3_tree

def parse_args() -> Dict[str, Any]:
    parser = ArgumentParser(description="i3-client example")
    parser.add_argument('--fpath', type=str, default='i3_tree.json', help='Path to the i3 tree JSON file')
    parser.add_argument('--grab', action='store_true', help='Grab the i3 tree from the running i3 instance')
    return parser.parse_args().__dict__

def find_focused_node(node: I3Node) -> Optional[I3Node]:
    """Recursively find the focused node in the i3 tree"""
    if node.focused:
        return node
    for child in chain(node.nodes, node.floating_nodes):
        focused = find_focused_node(child)
        if focused:
            return focused
    return None

def find_focused_workspace(node: I3Node, parent_workspace: Optional[I3Workspace] = None) -> Optional[I3Workspace]:
    """Recursively find the focused workspace in the i3 tree"""
    if isinstance(node, I3Workspace):
        parent_workspace = node
    if node.focused:
        return parent_workspace
    for child in chain(node.nodes, node.floating_nodes):
        focused = find_focused_workspace(child, parent_workspace)
        if focused:
            return focused
    return None

def print_node_info(tree: I3Node, indent: int = 0):
    # Print some info about the tree
    for node in tree.nodes:
        if not isinstance(node, I3Output):
            continue
        # yellow
        colour, reset = "\x1b[33m", "\x1b[0m"
        print(f"{colour}⎚ Output: {node.name}, focused: {node.focused}{reset}")
        for child in node.nodes:
            if not isinstance(child, I3Container):
                # italic
                colour, reset = "\x1b[3m", "\x1b[0m"
                print(f'  ▷{colour} Skipping non-container child node of output: {child.type}{reset}')
                continue
            for workspace in child.nodes:
                if not isinstance(workspace, I3Workspace):
                    colour, reset = "\x1b[3m", "\x1b[0m"
                    print(f'  ▷{colour} Skipping non-workspace child node of container: {workspace.type}{reset}')
                    continue
                # blue
                colour, reset = "\x1b[34m", "\x1b[0m"
                print(f"  {colour}▣{reset} Workspace {workspace.num}: {workspace.name}, focused: {workspace.focused}")
                for node in workspace.nodes:
                    colour, reset = "", ""
                    if node.focused:
                        colour, reset = "\x1b[32m", "\x1b[0m"
                    print(f"{colour}    ■ Node ID {node.id}, focused: {node.focused}{reset}")
                    print(f"{colour}      - {node.window_properties.instance}{reset}")
                    print(f"{colour}      - {node.name}{reset}")

def main():
    args = parse_args()
    if args['grab']:
        tree = get_i3_tree()
    else:
        tree = load_i3_tree(args['fpath'])

    print(f"Loaded i3 tree: {tree.type} node with {len(tree.nodes)} child nodes:\n")

    print_node_info(tree)

    focused = find_focused_node(tree)
    # pp.ppd(focused, indent=None)

    focused_workspace = find_focused_workspace(tree)
    if not focused_workspace:
        print("No focused workspace found")
        return

    print()
    pp.ppd({'focused_workspace': focused_workspace.name}, indent=None)
    for w in focused_workspace.get_windows():
        pp.ppd(
            {
                'focused': w.focused,
                'id': w.id,
                'window': {
                    'name': w.name,
                    'program': w.window_properties.instance,
                    'title': w.window_properties.title,
                }
            },
            indent=None
        )



if __name__ == "__main__":
    main()
