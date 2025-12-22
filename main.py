#!/usr/bin/env python3

from argparse import ArgumentParser
from dataclasses import dataclass, field
from itertools import chain
import json
from typing import Optional, List, Dict, Any
import subprocess

from pprint_ndjson import pp

@dataclass
class Rect:
    """Rectangle dimensions"""
    x: int
    y: int
    width: int
    height: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Rect':
        """Create Rect from dictionary"""
        return Rect(
            x=data['x'],
            y=data['y'],
            width=data['width'],
            height=data['height']
        )


@dataclass
class Gaps:
    """Workspace gap configuration"""
    inner: int
    outer: int
    top: int
    right: int
    bottom: int
    left: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Gaps':
        """Create Gaps from dictionary"""
        return Gaps(
            inner=data['inner'],
            outer=data['outer'],
            top=data['top'],
            right=data['right'],
            bottom=data['bottom'],
            left=data['left']
        )


@dataclass
class WindowProperties:
    """Window-specific properties"""
    class_: Optional[str] = field(default=None, metadata={'json_name': 'class'})
    instance: Optional[str] = None
    window_role: Optional[str] = None
    machine: Optional[str] = None
    title: Optional[str] = None
    transient_for: Optional[int] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WindowProperties':
        """Create WindowProperties from dictionary"""
        return WindowProperties(
            class_=data.get('class'),
            instance=data.get('instance'),
            window_role=data.get('window_role'),
            machine=data.get('machine'),
            title=data.get('title'),
            transient_for=data.get('transient_for')
        )


@dataclass
class Swallow:
    """Window swallow criteria for i3 layouts"""
    dock: Optional[int] = None
    insert_where: Optional[int] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Swallow':
        """Create Swallow from dictionary"""
        return Swallow(
            dock=data.get('dock'),
            insert_where=data.get('insert_where')
        )


@dataclass
class I3Node:
    """Base class for all i3 tree nodes"""
    id: int
    type: str
    orientation: str
    scratchpad_state: str
    percent: Optional[float]
    urgent: bool
    marks: List[str]
    focused: bool
    layout: str
    workspace_layout: str
    last_split_layout: str
    border: str
    current_border_width: int
    rect: Rect
    deco_rect: Rect
    window_rect: Rect
    geometry: Rect
    name: Optional[str]
    window_icon_padding: int
    window: Optional[int]
    window_type: Optional[str]
    nodes: List['I3Node'] = field(default_factory=list)
    floating_nodes: List['I3Node'] = field(default_factory=list)
    focus: List[int] = field(default_factory=list)
    fullscreen_mode: int = 0
    sticky: bool = False
    floating: str = "auto_off"
    swallows: List[Swallow] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'I3Node':
        """Create appropriate I3Node subclass from dictionary based on type"""
        node_type = data.get('type')

        # Determine the appropriate class
        if node_type == 'root':
            return I3Root._from_dict_internal(data)
        elif node_type == 'output':
            return I3Output._from_dict_internal(data)
        elif node_type == 'dockarea':
            return I3DockArea._from_dict_internal(data)
        elif node_type == 'workspace':
            return I3Workspace._from_dict_internal(data)
        elif node_type == 'floating_con':
            return I3FloatingContainer._from_dict_internal(data)
        else:  # 'con' and others
            return I3Container._from_dict_internal(data)

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3Node':
        """Internal method to create base I3Node fields"""
        # Parse nested nodes recursively
        nodes = [I3Node.from_dict(n) for n in data.get('nodes', [])]
        floating_nodes = [I3Node.from_dict(n) for n in data.get('floating_nodes', [])]
        swallows = [Swallow.from_dict(s) for s in data.get('swallows', [])]

        return I3Node(
            id=data['id'],
            type=data['type'],
            orientation=data['orientation'],
            scratchpad_state=data['scratchpad_state'],
            percent=data.get('percent'),
            urgent=data['urgent'],
            marks=data.get('marks', []),
            focused=data['focused'],
            layout=data['layout'],
            workspace_layout=data['workspace_layout'],
            last_split_layout=data['last_split_layout'],
            border=data['border'],
            current_border_width=data['current_border_width'],
            rect=Rect.from_dict(data['rect']),
            deco_rect=Rect.from_dict(data['deco_rect']),
            window_rect=Rect.from_dict(data['window_rect']),
            geometry=Rect.from_dict(data['geometry']),
            name=data.get('name'),
            window_icon_padding=data['window_icon_padding'],
            window=data.get('window'),
            window_type=data.get('window_type'),
            nodes=nodes,
            floating_nodes=floating_nodes,
            focus=data.get('focus', []),
            fullscreen_mode=data.get('fullscreen_mode', 0),
            sticky=data.get('sticky', False),
            floating=data.get('floating', 'auto_off'),
            swallows=swallows
        )


@dataclass
class I3Root(I3Node):
    """Root node of the i3 tree"""

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3Root':
        """Create I3Root from dictionary"""
        base = I3Node._from_dict_internal(data)
        return I3Root(**base.__dict__)

    def get_outputs(self) -> List['I3Output']:
        """Get all output nodes from the root"""
        return [node for node in self.nodes if isinstance(node, I3Output)]


@dataclass
class I3Output(I3Node):
    """Output (monitor) node"""

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3Output':
        """Create I3Output from dictionary"""
        base = I3Node._from_dict_internal(data)
        return I3Output(**base.__dict__)

    def get_containers(self) -> List['I3Container']:
        """Get all container nodes from the output"""
        return [node for node in self.nodes if isinstance(node, I3Container)]


@dataclass
class I3DockArea(I3Node):
    """Dockarea for bars and docked windows"""
    output: Optional[str] = None
    actual_deco_rect: Optional[Rect] = None

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3DockArea':
        """Create I3DockArea from dictionary"""
        base = I3Node._from_dict_internal(data)
        actual_deco = data.get('actual_deco_rect')
        return I3DockArea(
            **base.__dict__,
            output=data.get('output'),
            actual_deco_rect=Rect.from_dict(actual_deco) if actual_deco else None
        )


@dataclass
class I3Container(I3Node):
    """Regular container node"""
    output: Optional[str] = None
    window_properties: Optional[WindowProperties] = None
    actual_deco_rect: Optional[Rect] = None

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3Container':
        """Create I3Container from dictionary"""
        base = I3Node._from_dict_internal(data)
        window_props = data.get('window_properties')
        actual_deco = data.get('actual_deco_rect')
        return I3Container(
            **base.__dict__,
            output=data.get('output'),
            window_properties=WindowProperties.from_dict(window_props) if window_props else None,
            actual_deco_rect=Rect.from_dict(actual_deco) if actual_deco else None
        )

    def get_workspaces(self) -> List['I3Workspace']:
        """Get all workspace nodes from the container"""
        return [node for node in self.nodes if isinstance(node, I3Workspace)]


@dataclass
class I3Workspace(I3Node):
    """Workspace node"""
    num: int = 0
    gaps: Optional[Gaps] = None
    output: Optional[str] = None

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3Workspace':
        """Create I3Workspace from dictionary"""
        base = I3Node._from_dict_internal(data)
        gaps_data = data.get('gaps')
        return I3Workspace(
            **base.__dict__,
            num=data.get('num', 0),
            gaps=Gaps.from_dict(gaps_data) if gaps_data else None,
            output=data.get('output')
        )


@dataclass
class I3FloatingContainer(I3Node):
    """Floating container node"""
    output: Optional[str] = None

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3FloatingContainer':
        """Create I3FloatingContainer from dictionary"""
        base = I3Node._from_dict_internal(data)
        return I3FloatingContainer(
            **base.__dict__,
            output=data.get('output')
        )

def load_i3_tree(fpath: str = 'i3_tree.json') -> I3Node:
    """Load and parse i3 tree from JSON file"""
    return I3Node.from_dict(json.load(open(fpath, 'r')))

def get_i3_tree() -> I3Node:
    """Get the current i3 tree from the i3 window manager"""
    result = subprocess.run(['i3-msg', '-t', 'get_tree'], capture_output=True, text=True)
    return I3Node.from_dict(json.loads(result.stdout))

def parse_args() -> Dict[str, Any]:
    parser = ArgumentParser(description="i3-client example")
    parser.add_argument('--fpath', type=str, default='i3_tree.json', help='Path to the i3 tree JSON file')
    parser.add_argument('--grab', action='store_true', help='Grab the i3 tree from the running i3 instance')
    return parser.parse_args().__dict__

def find_focused_node(node: I3Node) -> Optional[I3Node]:
    """Recursively find the focused node in the i3 tree"""
    if node.focused:
        return node
    for child in node.nodes:
        focused = find_focused_node(child)
        if focused:
            return focused
    for child in node.floating_nodes:
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
    for child in node.nodes:
        focused = find_focused_workspace(child, parent_workspace)
        if focused:
            return focused
    for child in node.floating_nodes:
        focused = find_focused_workspace(child)
        if focused:
            return focused
    return None

def get_workspace(tree: I3Node, workspace_id: str) -> Optional[I3Workspace]:
    """Get a workspace by its ID (name)"""
    for output in tree.get_outputs():
        for container in output.get_containers():
            for workspace in container.get_workspaces():
                if workspace.name == workspace_id:
                    return workspace

    raise ValueError(f"Workspace with ID {workspace_id} not found")

def windows_in_workspace(workspace: I3Workspace) -> List[I3Node]:
    """Get all windows in a specified workspace"""
    result = []

    def _collect_windows(node: I3Node):
        for child in node.nodes:
            if not child.nodes:
                result.append(child)
        for child in chain(node.nodes, node.floating_nodes):
            _collect_windows(child)

    _collect_windows(workspace)
    return result


def print_node_info(tree: I3Node):
    'Print some info about the tree'
    for node in tree.nodes:
        if not isinstance(node, I3Output):
            continue
        print(f"  Output: {node.name}, focused: {node.focused}")
        for child in node.nodes:
            if not isinstance(child, I3Container):
                print(f'    Skipping non-container child node of output: {child.type}')
                continue
            for workspace in child.nodes:
                if not isinstance(workspace, I3Workspace):
                    print(f'    Skipping non-workspace child node of container: {workspace.type}')
                    continue
                print(f"    Workspace {workspace.num}: {workspace.name}, focused: {workspace.focused}")
                for node in workspace.nodes:
                    colour, reset = "", ""
                    if node.focused:
                        colour, reset = "\x1b[32m", "\x1b[0m"
                    print(f"{colour}      Node ID {node.id}: {node.name} (type: {node.type}), focused: {node.focused}{reset}")

def main():
    print("Hello from i3-client!")

    args = parse_args()
    if args['grab']:
        tree = get_i3_tree()
    else:
        tree = load_i3_tree(args['fpath'])

    print(f"Loaded i3 tree: {tree.type} node with {len(tree.nodes)} child nodes")

    focused = find_focused_node(tree)
    pp.ppd({
        'program': focused.window_properties.instance,
        'name': focused.name,
    }, indent=2)

    focused_workspace = find_focused_workspace(tree)
    pp.ppd({'focused_workspace': focused_workspace.name}, indent=None)

    other_windows = windows_in_workspace(focused_workspace)
    for w in other_windows:
        pp.ppd({
            'id': w.id,
            'name': w.name,
            'focused': w.focused,
            'program': w.window_properties.instance if w.window_properties else None,
        }, indent=2)



if __name__ == "__main__":
    main()
