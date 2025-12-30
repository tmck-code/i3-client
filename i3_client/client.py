#!/usr/bin/env python3

from __future__ import annotations
from dataclasses import dataclass, field
import json
from typing import Optional, List, Dict, Any
import subprocess
from typing import Iterable

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
            if data.get('window') is not None:
                return I3Window._from_dict_internal(data)
            else:
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


@dataclass
class I3Output(I3Node):
    """Output (monitor) node"""

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3Output':
        """Create I3Output from dictionary"""
        base = I3Node._from_dict_internal(data)
        return I3Output(**base.__dict__)


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
class I3Window(I3Node):
    """Window node"""
    window_properties: WindowProperties = field(default_factory=WindowProperties)

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> I3Window:
        """Create I3Window from dictionary"""
        base = I3Node._from_dict_internal(data)
        return I3Window(
            **base.__dict__,
            window_properties=WindowProperties.from_dict(data['window_properties'])
        )


@dataclass
class I3Container(I3Node):
    """Regular container node"""
    output: Optional[str] = None
    actual_deco_rect: Optional[Rect] = None

    @staticmethod
    def _from_dict_internal(data: Dict[str, Any]) -> 'I3Container':
        """Create I3Container from dictionary"""
        base = I3Node._from_dict_internal(data)
        actual_deco = data.get('actual_deco_rect')
        return I3Container(
            **base.__dict__,
            output=data.get('output'),
            actual_deco_rect=Rect.from_dict(actual_deco) if actual_deco else None
        )

    def get_windows(self) -> Iterable['I3Node']:
        """Yield all nodes in this container (recursively) that have a window property (i.e., are windows), including floating nodes."""
        for node in self.nodes + self.floating_nodes:
            if getattr(node, 'window', None) is not None:
                yield node
            # Only recurse if node is a container/workspace/floating container
            if isinstance(node, (I3Container, I3Workspace, I3FloatingContainer)):
                yield from node.get_windows()

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

    def get_windows(self) -> Iterable['I3Node']:
        """Yield all nodes in this workspace (recursively) that have a window property (i.e., are windows), including floating nodes."""
        for node in self.nodes + self.floating_nodes:
            if getattr(node, 'window', None) is not None:
                yield node
            # Only recurse if node is a container/workspace/floating container
            if isinstance(node, (I3Container, I3Workspace, I3FloatingContainer)):
                yield from node.get_windows()


@dataclass
class I3FloatingContainer(I3Node):
    """Floating container node"""
    output: Optional[str] = None

    def get_windows(self) -> Iterable['I3Node']:
        """Yield all nodes in this floating container (recursively) that have a window property (i.e., are windows), including floating nodes."""
        for node in self.nodes + self.floating_nodes:
            if getattr(node, 'window', None) is not None:
                yield node
            if isinstance(node, (I3Container, I3Workspace, I3FloatingContainer)):
                yield from node.get_windows()

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
