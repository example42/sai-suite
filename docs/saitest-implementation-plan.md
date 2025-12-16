# Saitest Implementation Plan with LangGraph

## Overview

Saitest is an agent-based verification tool that installs software in containerized environments, observes system changes, and generates validated saidata using AI-powered analysis.

## Architecture

### High-Level Flow
```
Input (software name) 
  → Discovery Agent (research installation methods)
  → Platform Selection Agent (choose OS/versions to test)
  → Installation Agents (parallel, per platform)
  → Inspection Agents (analyze installed system)
  → Analysis Agent (synthesize observations)
  → Generation Agent (create saidata)
  → Quality Agent (validate and score)
  → Output (validated saidata + report)
```

### Technology Stack
- **Agent Framework**: LangGraph
- **LLM Providers**: OpenAI, Anthropic, Ollama (configurable)
- **Container Runtime**: Docker (via docker-py)
- **System Monitoring**: watchdog, psutil, inotify
- **Data Models**: Pydantic (shared with saigen)
- **Schema Validation**: jsonschema
- **Configuration**: YAML/JSON
- **CLI**: Click or Typer

## Repository Structure

Saitest will be part of the **sai-suite monorepo** alongside sai and saigen.

### Rationale for Monorepo Approach

**Why keep saitest in sai-suite:**
- **Shared domain models**: Direct access to saidata models from saigen
- **Natural workflow**: `saigen generate` → `saitest verify` → `sai install`
- **Code reuse**: Schema validation, configuration utilities, repository downloaders
- **Unified documentation**: Single source for all SAI tools
- **Easier integration**: No cross-repo dependency management
- **Consistent tooling**: Same CI/CD, testing, linting setup

**Dependency management:**
Use optional dependencies in `pyproject.toml` to keep installations lightweight:
```toml
[project.optional-dependencies]
saitest = [
    "langgraph>=0.1",
    "docker>=7.0",
    "watchdog>=3.0",
]
```

Users install only what they need:
```bash
pip install sai-suite              # Just sai
pip install sai-suite[saigen]      # sai + saigen
pip install sai-suite[saitest]     # sai + saitest
pip install sai-suite[all]         # Everything
```

### Monorepo Structure

```
sai-suite/
├── sai/                    # Execution tool (stable)
│   ├── cli/
│   ├── core/
│   ├── providers/
│   ├── docs/              # Sai-specific docs
│   └── ...
├── saigen/                 # Generation tool (stable)
│   ├── cli/
│   ├── core/
│   ├── llm/
│   ├── repositories/
│   ├── docs/              # Saigen-specific docs
│   └── ...
├── saitest/                # Verification tool (experimental)
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── commands/
│   │       ├── verify.py
│   │       ├── test.py
│   │       └── report.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py    # Main LangGraph workflow
│   │   ├── state.py           # State definitions
│   │   └── config.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── discovery.py
│   │   ├── platform.py
│   │   ├── installation.py
│   │   ├── inspection.py
│   │   ├── analysis.py
│   │   ├── generation.py
│   │   └── quality.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── container.py
│   │   ├── package.py
│   │   ├── system.py
│   │   └── monitoring.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── observation.py
│   │   └── report.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── docker_manager.py
│   │   ├── fs_monitor.py
│   │   └── validators.py
│   └── docs/              # Saitest-specific docs
│       ├── README.md
│       ├── architecture.md
│       ├── cli-reference.md
│       └── examples/
├── shared/                 # Shared code across tools (if needed)
│   ├── models/
│   │   └── saidata.py     # Common saidata models
│   └── utils/
│       └── validation.py
├── schemas/               # Shared JSON schemas
│   ├── saidata-0.3-schema.json
│   ├── providerdata-0.1-schema.json
│   └── ...
├── docs/                  # General/cross-tool documentation
│   ├── README.md          # Overview of all tools
│   ├── installation.md
│   ├── architecture.md
│   ├── workflows.md       # How tools work together
│   └── summaries/
├── tests/
│   ├── sai/
│   ├── saigen/
│   ├── saitest/           # Saitest tests
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── shared/
│   └── integration/       # Cross-tool integration tests
├── scripts/
│   └── development/
│       ├── sai/
│       ├── saigen/
│       └── saitest/       # Saitest demo scripts
└── pyproject.toml         # Unified dependencies with optional extras
```

### Documentation Organization

Following the existing pattern:
- **Tool-specific docs**: `sai/docs/`, `saigen/docs/`, `saitest/docs/`
- **General docs**: `docs/` (installation, architecture, cross-tool workflows)
- **Examples**: Within each tool's docs directory
- **Summaries**: `docs/summaries/` for implementation notes

### Code Sharing Strategy

Saitest will import from saigen where appropriate:
```python
# Saitest can directly import from saigen
from saigen.models.saidata import SaidataModel
from saigen.utils.validation import validate_saidata
from saigen.repositories import RepositoryDownloader

# Saitest-specific models
from saitest.models.observation import Observation
from saitest.core.state import VerificationState
```

### Migration Path (if needed)

If saitest grows significantly or needs independent releases:
1. Extract to separate `saitest` repository
2. Create `sai-models` package for shared code
3. Both repos depend on `sai-models`

But starting in the monorepo provides maximum flexibility and code reuse.

## Saitest Package Structure

Within the saitest directory
    └── fixtures/
```

## Phase 1: Core Infrastructure (Week 1-2)

### 1.1 State Definition

**File**: `saitest/core/state.py`

```python
from typing import TypedDict, List, Dict, Optional, Annotated
from pydantic import BaseModel, Field
import operator

class Observation(BaseModel):
    """Single observation from system monitoring"""
    type: str  # file, service, port, command, package
    platform: str
    timestamp: str
    data: Dict
    confidence: float = 1.0

class PlatformResult(BaseModel):
    """Results from testing one platform"""
    platform: str
    success: bool
    observations: List[Observation]
    errors: List[str]
    duration: float

class VerificationState(TypedDict):
    """Main state for LangGraph workflow"""
    # Input
    software: str
    input_saidata: Optional[Dict]
    target_platforms: Optional[List[str]]
    
    # Discovery phase
    discovery_complete: bool
    installation_methods: List[str]
    expected_services: List[str]
    expected_files: List[str]
    expected_ports: List[int]
    
    # Platform selection
    selected_platforms: List[str]
    
    # Installation phase
    current_platform: Optional[str]
    platform_results: Annotated[List[PlatformResult], operator.add]
    
    # Analysis phase
    aggregated_observations: Dict[str, List[Observation]]
    patterns: Dict[str, any]
    variations: Dict[str, Dict]
    
    # Generation phase
    generated_saidata: Optional[Dict]
    confidence_scores: Dict[str, float]
    
    # Quality check
    validation_errors: List[str]
    completeness_score: float
    accuracy_score: float
    overall_confidence: float
    
    # Control flow
    retry_count: int
    max_retries: int
    needs_human_review: bool
    
    # Metadata
    start_time: str
    messages: Annotated[List[str], operator.add]
```


### 1.2 Container Management

**File**: `saitest/utils/docker_manager.py`

```python
import docker
from typing import Optional, Dict, List
from contextlib import contextmanager

class ContainerManager:
    """Manages Docker containers for testing"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.active_containers = {}
    
    def get_image_for_platform(self, platform: str) -> str:
        """Map platform string to Docker image"""
        mapping = {
            "ubuntu:22.04": "ubuntu:22.04",
            "ubuntu:24.04": "ubuntu:24.04",
            "debian:11": "debian:11",
            "debian:12": "debian:12",
            "fedora:39": "fedora:39",
            "fedora:40": "fedora:40",
            "rocky:8": "rockylinux:8",
            "rocky:9": "rockylinux:9",
        }
        return mapping.get(platform, platform)
    
    @contextmanager
    def spawn_container(self, platform: str, name: Optional[str] = None):
        """Spawn container and ensure cleanup"""
        image = self.get_image_for_platform(platform)
        
        # Pull image if needed
        try:
            self.client.images.get(image)
        except docker.errors.ImageNotFound:
            print(f"Pulling image {image}...")
            self.client.images.pull(image)
        
        # Create container
        container = self.client.containers.run(
            image,
            name=name,
            detach=True,
            tty=True,
            remove=False,
            privileged=True,
        )
        
        self.active_containers[platform] = container
        
        try:
            yield ContainerWrapper(container)
        finally:
            container.stop()
            container.remove()
            del self.active_containers[platform]

class ContainerWrapper:
    """Wrapper for container operations"""
    
    def __init__(self, container):
        self.container = container
    
    def exec(self, command: str, **kwargs) -> Dict:
        """Execute command in container"""
        exit_code, output = self.container.exec_run(command, **kwargs)
        return {
            "exit_code": exit_code,
            "output": output.decode('utf-8'),
            "success": exit_code == 0
        }
    
    def read_file(self, path: str) -> Optional[str]:
        """Read file from container"""
        result = self.exec(f"cat {path}")
        return result["output"] if result["success"] else None
    
    def list_files(self, path: str) -> List[str]:
        """List files in directory"""
        result = self.exec(f"find {path} -type f")
        if result["success"]:
            return result["output"].strip().split('\n')
        return []
```

#
## 1.3 System Monitoring Tools

**File**: `saitest/utils/fs_monitor.py`

```python
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FileChange:
    path: str
    change_type: str  # created, modified, deleted
    timestamp: datetime
    size: Optional[int] = None
    permissions: Optional[str] = None

class FilesystemMonitor:
    """Monitor filesystem changes during installation"""
    
    def __init__(self, container):
        self.container = container
        self.baseline = None
        self.changes = []
    
    def capture_baseline(self):
        """Capture filesystem state before installation"""
        result = self.container.exec("find / -type f 2>/dev/null")
        self.baseline = set(result["output"].strip().split('\n'))
    
    def capture_changes(self) -> List[FileChange]:
        """Capture changes after installation"""
        result = self.container.exec("find / -type f 2>/dev/null")
        current = set(result["output"].strip().split('\n'))
        
        new_files = current - self.baseline
        
        changes = []
        for path in new_files:
            stat_result = self.container.exec(f"stat -c '%s %a' {path}")
            if stat_result["success"]:
                size, perms = stat_result["output"].strip().split()
                changes.append(FileChange(
                    path=path,
                    change_type="created",
                    timestamp=datetime.now(),
                    size=int(size),
                    permissions=perms
                ))
        
        return changes
    
    def get_service_files(self) -> List[str]:
        """Find systemd service files"""
        result = self.container.exec(
            "find /etc/systemd /usr/lib/systemd -name '*.service' 2>/dev/null"
        )
        if result["success"]:
            return result["output"].strip().split('\n')
        return []
    
    def get_binaries(self) -> List[str]:
        """Find executable binaries in PATH"""
        result = self.container.exec(
            "find /usr/bin /usr/sbin /usr/local/bin -type f -executable 2>/dev/null"
        )
        if result["success"]:
            return result["output"].strip().split('\n')
        return []
```

## Phase 2: LangGraph Tools (Week 2-3)

### 2.1 Tool Definitions

**File**: `saitest/tools/package.py`

```python
from langchain_core.tools import tool
from typing import Dict, List
from ..utils.docker_manager import ContainerManager

container_manager = ContainerManager()

@tool
def install_package_apt(platform: str, package: str) -> Dict:
    """
    Install a package using apt on specified platform.
    
    Args:
        platform: Platform identifier (e.g., "ubuntu:22.04")
        package: Package name to install
    
    Returns:
        Dict with installation results and observations
    """
    with container_manager.spawn_container(platform) as container:
        container.exec("apt-get update -qq")
        
        from ..utils.fs_monitor import FilesystemMonitor
        monitor = FilesystemMonitor(container)
        monitor.capture_baseline()
        
        result = container.exec(f"apt-get install -y {package}")
        
        file_changes = monitor.capture_changes()
        services = monitor.get_service_files()
        binaries = monitor.get_binaries()
        
        return {
            "success": result["success"],
            "output": result["output"],
            "files_created": [f.path for f in file_changes],
            "services_found": services,
            "binaries_found": binaries,
            "platform": platform
        }
```

**Fil
e**: `saitest/tools/system.py`

```python
from langchain_core.tools import tool
from typing import Dict, List

@tool
def inspect_service(platform: str, service_name: str) -> Dict:
    """Inspect systemd service configuration."""
    with container_manager.spawn_container(platform) as container:
        status = container.exec(f"systemctl status {service_name}")
        cat_result = container.exec(f"systemctl cat {service_name}")
        enabled = container.exec(f"systemctl is-enabled {service_name}")
        
        return {
            "service_name": service_name,
            "status": status["output"],
            "config": cat_result["output"] if cat_result["success"] else None,
            "enabled": enabled["output"].strip() == "enabled",
            "platform": platform
        }

@tool
def check_listening_ports(platform: str) -> List[Dict]:
    """Check which ports are listening after installation."""
    with container_manager.spawn_container(platform) as container:
        result = container.exec("ss -tlnp")
        
        ports = []
        if result["success"]:
            for line in result["output"].split('\n')[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        local_addr = parts[3]
                        if ':' in local_addr:
                            port = local_addr.split(':')[-1]
                            ports.append({
                                "port": int(port),
                                "protocol": "tcp",
                                "address": local_addr
                            })
        return ports
```

## Phase 3: Agent Nodes (Week 3-4)

### 3.1 Discovery Agent

**File**: `saitest/agents/discovery.py`

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..core.state import VerificationState
import json

def discovery_agent(state: VerificationState) -> VerificationState:
    """
    Discovery agent researches software and plans verification.
    Uses LLM to identify installation methods, services, files, ports.
    """
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    system_prompt = """You are a software installation expert. Given a software name,
    research and provide detailed information about how it's typically installed and configured
    on Linux systems.
    
    Return a JSON object with:
    {
        "installation_methods": ["apt", "dnf", "source", "binary"],
        "package_names": {"apt": "package-name", "dnf": "package-name"},
        "expected_services": ["service-name"],
        "expected_files": ["/path/to/binary", "/path/to/config"],
        "expected_ports": [80, 443],
        "config_locations": ["/etc/software"],
        "description": "Brief description"
    }
    """
    
    user_prompt = f"""Research the software: {state['software']}
    
    Provide comprehensive installation and configuration information.
    Focus on Debian/Ubuntu (apt) and RedHat/Fedora (dnf) systems.
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    
    try:
        discovery_data = json.loads(response.content)
        
        state["installation_methods"] = discovery_data.get("installation_methods", [])
        state["expected_services"] = discovery_data.get("expected_services", [])
        state["expected_files"] = discovery_data.get("expected_files", [])
        state["expected_ports"] = discovery_data.get("expected_ports", [])
        state["discovery_complete"] = True
        state["messages"].append(f"Discovery complete: found {len(state['installation_methods'])} methods")
        
    except json.JSONDecodeError:
        state["messages"].append("Discovery failed: invalid JSON response")
        state["discovery_complete"] = False
    
    return state
```

#
## 3.2 Platform Selection Agent

**File**: `saitest/agents/platform.py`

```python
from langchain_openai import ChatOpenAI
from ..core.state import VerificationState
import json

def platform_selection_agent(state: VerificationState) -> VerificationState:
    """Select optimal platforms to test based on discovery results."""
    
    if state.get("target_platforms"):
        state["selected_platforms"] = state["target_platforms"]
        return state
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = f"""Given this software: {state['software']}
    
    Installation methods available: {state['installation_methods']}
    
    Select 2-4 platforms to test that provide good coverage.
    Consider different package managers and popular distributions.
    
    Available: ubuntu:22.04, ubuntu:24.04, debian:11, debian:12, fedora:39, rocky:9
    
    Return JSON array: ["platform1", "platform2"]
    """
    
    response = llm.invoke(prompt)
    
    try:
        platforms = json.loads(response.content)
        state["selected_platforms"] = platforms
        state["messages"].append(f"Selected {len(platforms)} platforms")
    except json.JSONDecodeError:
        state["selected_platforms"] = ["ubuntu:22.04", "debian:12"]
        state["messages"].append("Using default platforms")
    
    return state
```

### 3.3 Installation Agent

**File**: `saitest/agents/installation.py`

```python
from langchain_openai import ChatOpenAI
from ..core.state import VerificationState, PlatformResult, Observation
from ..tools.package import install_package_apt
from datetime import datetime
import time

def installation_agent(state: VerificationState) -> VerificationState:
    """Install software on current platform and collect observations."""
    
    platform = state["current_platform"]
    software = state["software"]
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools([install_package_apt])
    
    prompt = f"""Install {software} on {platform}.
    Expected methods: {state['installation_methods']}
    Use the appropriate tool to install the package.
    """
    
    start_time = time.time()
    
    try:
        response = llm.invoke(prompt)
        
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            result = install_package_apt.invoke(tool_call["args"])
            
            observations = []
            
            for file_path in result.get("files_created", []):
                observations.append(Observation(
                    type="file",
                    platform=platform,
                    timestamp=datetime.now().isoformat(),
                    data={"path": file_path},
                    confidence=1.0
                ))
            
            for service in result.get("services_found", []):
                observations.append(Observation(
                    type="service",
                    platform=platform,
                    timestamp=datetime.now().isoformat(),
                    data={"path": service},
                    confidence=0.9
                ))
            
            platform_result = PlatformResult(
                platform=platform,
                success=result["success"],
                observations=observations,
                errors=[],
                duration=time.time() - start_time
            )
            
            state["platform_results"].append(platform_result)
            state["messages"].append(f"Installation on {platform}: {len(observations)} observations")
            
    except Exception as e:
        platform_result = PlatformResult(
            platform=platform,
            success=False,
            observations=[],
            errors=[str(e)],
            duration=time.time() - start_time
        )
        state["platform_results"].append(platform_result)
    
    return state
```

###
 3.4 Analysis Agent

**File**: `saitest/agents/analysis.py`

```python
from langchain_openai import ChatOpenAI
from ..core.state import VerificationState
import json

def analysis_agent(state: VerificationState) -> VerificationState:
    """Analyze observations across platforms to identify patterns."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # Aggregate observations by type
    observations_by_type = {}
    for result in state["platform_results"]:
        if not result.success:
            continue
        
        for obs in result.observations:
            if obs.type not in observations_by_type:
                observations_by_type[obs.type] = []
            observations_by_type[obs.type].append({
                "platform": result.platform,
                "data": obs.data,
                "confidence": obs.confidence
            })
    
    state["aggregated_observations"] = observations_by_type
    
    prompt = f"""Analyze observations from installing {state['software']}:

{json.dumps(observations_by_type, indent=2)}

Identify:
1. Common patterns (same across all platforms)
2. Platform-specific variations
3. Confidence level for each finding

Return JSON:
{{
    "common_packages": [{{"name": "...", "package_name": "..."}}],
    "common_services": [{{"name": "...", "type": "systemd"}}],
    "common_files": [{{"path": "...", "purpose": "..."}}],
    "common_commands": [{{"name": "...", "path": "..."}}],
    "common_ports": [80, 443],
    "variations": {{"ubuntu:22.04": {{"packages": [...]}}}},
    "confidence": {{"packages": 0.95, "services": 0.90}}
}}
"""
    
    response = llm.invoke(prompt)
    
    try:
        analysis = json.loads(response.content)
        state["patterns"] = {
            "packages": analysis.get("common_packages", []),
            "services": analysis.get("common_services", []),
            "files": analysis.get("common_files", []),
            "commands": analysis.get("common_commands", []),
            "ports": analysis.get("common_ports", [])
        }
        state["variations"] = analysis.get("variations", {})
        state["confidence_scores"] = analysis.get("confidence", {})
        state["messages"].append("Analysis complete")
    except json.JSONDecodeError:
        state["messages"].append("Analysis failed")
    
    return state
```

### 3.5 Generation Agent

**File**: `saitest/agents/generation.py`

```python
from langchain_openai import ChatOpenAI
from ..core.state import VerificationState
import yaml
import json

def generation_agent(state: VerificationState) -> VerificationState:
    """Generate saidata YAML from analyzed patterns."""
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = f"""Generate saidata YAML for {state['software']} following schema 0.3.

Common patterns:
{json.dumps(state['patterns'], indent=2)}

Platform variations:
{json.dumps(state['variations'], indent=2)}

Generate complete saidata with:
- version: "0.3"
- metadata: name, description, homepage, license
- packages: name, package_name, version
- services: name, type, enabled
- files: path, purpose
- commands: name, path
- ports: number, protocol
- providers: provider-specific overrides

Return only valid YAML.
"""
    
    response = llm.invoke(prompt)
    
    try:
        saidata = yaml.safe_load(response.content)
        state["generated_saidata"] = saidata
        state["messages"].append("Saidata generated")
    except yaml.YAMLError as e:
        state["messages"].append(f"Generation failed: {e}")
        state["generated_saidata"] = None
    
    return state
```

### 3.
6 Quality Check Agent

**File**: `saitest/agents/quality.py`

```python
from langchain_openai import ChatOpenAI
from ..core.state import VerificationState
import jsonschema
import json
import yaml

def quality_check_agent(state: VerificationState) -> VerificationState:
    """Validate generated saidata and assess quality."""
    
    if not state["generated_saidata"]:
        state["overall_confidence"] = 0.0
        state["needs_human_review"] = True
        return state
    
    # Schema validation
    with open("schemas/saidata-0.3-schema.json") as f:
        schema = json.load(f)
    
    try:
        jsonschema.validate(state["generated_saidata"], schema)
        state["validation_errors"] = []
    except jsonschema.ValidationError as e:
        state["validation_errors"] = [str(e)]
    
    # LLM quality assessment
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = f"""Assess quality of this saidata:

{yaml.dump(state['generated_saidata'])}

Original observations:
{json.dumps(state['aggregated_observations'], indent=2)}

Evaluate:
1. Completeness: All observed resources included?
2. Accuracy: Values match observations?
3. Schema compliance: Valid structure?

Return JSON:
{{
    "completeness_score": 0.0-1.0,
    "accuracy_score": 0.0-1.0,
    "overall_confidence": 0.0-1.0,
    "issues": ["issue1"],
    "recommendations": ["rec1"]
}}
"""
    
    response = llm.invoke(prompt)
    
    try:
        assessment = json.loads(response.content)
        state["completeness_score"] = assessment.get("completeness_score", 0.0)
        state["accuracy_score"] = assessment.get("accuracy_score", 0.0)
        state["overall_confidence"] = assessment.get("overall_confidence", 0.0)
        
        if state["overall_confidence"] < 0.7 or state["validation_errors"]:
            state["needs_human_review"] = True
        else:
            state["needs_human_review"] = False
        
        state["messages"].append(f"Quality: {state['overall_confidence']:.2f}")
    except json.JSONDecodeError:
        state["overall_confidence"] = 0.0
        state["needs_human_review"] = True
    
    return state
```

## Phase 4: LangGraph Workflow (Week 4-5)

### 4.1 Main Orchestrator

**File**: `saitest/core/orchestrator.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from ..core.state import VerificationState
from ..agents import (
    discovery_agent,
    platform_selection_agent,
    installation_agent,
    analysis_agent,
    generation_agent,
    quality_check_agent
)
from datetime import datetime

def create_verification_workflow():
    """Create the main LangGraph workflow"""
    
    workflow = StateGraph(VerificationState)
    
    # Add nodes
    workflow.add_node("discovery", discovery_agent)
    workflow.add_node("platform_selection", platform_selection_agent)
    workflow.add_node("installation", installation_agent)
    workflow.add_node("analysis", analysis_agent)
    workflow.add_node("generation", generation_agent)
    workflow.add_node("quality_check", quality_check_agent)
    
    # Set entry point
    workflow.set_entry_point("discovery")
    
    # Flow
    workflow.add_edge("discovery", "platform_selection")
    
    workflow.add_conditional_edges(
        "platform_selection",
        route_to_platforms,
        {"installation": "installation", "analysis": "analysis"}
    )
    
    workflow.add_conditional_edges(
        "installation",
        check_more_platforms,
        {"installation": "installation", "analysis": "analysis"}
    )
    
    workflow.add_edge("analysis", "generation")
    workflow.add_edge("generation", "quality_check")
    
    workflow.add_conditional_edges(
        "quality_check",
        route_after_quality_check,
        {END: END, "retry": "installation"}
    )
    
    # Compile with checkpointing
    memory = SqliteSaver.from_conn_string(":memory:")
    app = workflow.compile(checkpointer=memory)
    
    return app

def route_to_platforms(state: VerificationState) -> str:
    """Route to first platform or analysis"""
    if state["selected_platforms"]:
        state["current_platform"] = state["selected_platforms"][0]
        return "installation"
    return "analysis"

def check_more_platforms(state: VerificationState) -> str:
    """Check if more platforms need testing"""
    tested = {r.platform for r in state["platform_results"]}
    remaining = [p for p in state["selected_platforms"] if p not in tested]
    
    if remaining:
        state["current_platform"] = remaining[0]
        return "installation"
    return "analysis"

def route_after_quality_check(state: VerificationState) -> str:
    """Route based on quality check results"""
    if state["overall_confidence"] < 0.5 and state["retry_count"] < state["max_retries"]:
        state["retry_count"] += 1
        return "retry"
    return END
```

de
f run_verification(software: str, platforms: list = None, config: dict = None):
    """Run verification workflow"""
    
    app = create_verification_workflow()
    
    initial_state = {
        "software": software,
        "input_saidata": None,
        "target_platforms": platforms,
        "discovery_complete": False,
        "installation_methods": [],
        "expected_services": [],
        "expected_files": [],
        "expected_ports": [],
        "selected_platforms": [],
        "current_platform": None,
        "platform_results": [],
        "aggregated_observations": {},
        "patterns": {},
        "variations": {},
        "generated_saidata": None,
        "confidence_scores": {},
        "validation_errors": [],
        "completeness_score": 0.0,
        "accuracy_score": 0.0,
        "overall_confidence": 0.0,
        "retry_count": 0,
        "max_retries": 2,
        "needs_human_review": False,
        "start_time": datetime.now().isoformat(),
        "messages": []
    }
    
    config = {"configurable": {"thread_id": "1"}}
    result = app.invoke(initial_state, config)
    
    return result
```

## Phase 5: CLI Interface (Week 5-6)

### 5.1 Main CLI

**File**: `saitest/cli/main.py`

```python
import click
from ..core.orchestrator import run_verification
import yaml
import json

@click.group()
@click.version_option()
def cli():
    """Saitest - Agent-based saidata verification tool"""
    pass

@cli.command()
@click.argument('software')
@click.option('--platforms', '-p', multiple=True)
@click.option('--output', '-o', type=click.Path())
@click.option('--format', type=click.Choice(['yaml', 'json']), default='yaml')
@click.option('--verbose', '-v', is_flag=True)
def verify(software, platforms, output, format, verbose):
    """Verify software and generate saidata"""
    
    click.echo(f"🔍 Verifying {software}...")
    
    result = run_verification(
        software=software,
        platforms=list(platforms) if platforms else None
    )
    
    if verbose:
        click.echo("\n📋 Messages:")
        for msg in result["messages"]:
            click.echo(f"  {msg}")
    
    click.echo(f"\n✅ Verification complete!")
    click.echo(f"  Confidence: {result['overall_confidence']:.2%}")
    click.echo(f"  Platforms tested: {len(result['platform_results'])}")
    
    if result["validation_errors"]:
        click.echo(f"\n⚠️  Validation errors:")
        for error in result["validation_errors"]:
            click.echo(f"  - {error}")
    
    if output and result["generated_saidata"]:
        with open(output, 'w') as f:
            if format == 'yaml':
                yaml.dump(result["generated_saidata"], f, default_flow_style=False)
            else:
                json.dump(result["generated_saidata"], f, indent=2)
        click.echo(f"\n💾 Saved to {output}")
    elif result["generated_saidata"]:
        click.echo("\n📄 Generated saidata:")
        click.echo(yaml.dump(result["generated_saidata"], default_flow_style=False))

@cli.command()
@click.argument('saidata_file', type=click.Path(exists=True))
@click.option('--platforms', '-p', multiple=True)
def test(saidata_file, platforms):
    """Test existing saidata file"""
    
    click.echo(f"🧪 Testing {saidata_file}...")
    
    with open(saidata_file) as f:
        saidata = yaml.safe_load(f)
    
    software = saidata.get("metadata", {}).get("name")
    
    if not software:
        click.echo("❌ No software name found")
        return
    
    result = run_verification(
        software=software,
        platforms=list(platforms) if platforms else None
    )
    
    click.echo(f"\n📊 Comparison:")
    click.echo(f"  Existing packages: {len(saidata.get('packages', []))}")
    click.echo(f"  Observed packages: {len(result['patterns'].get('packages', []))}")
    click.echo(f"  Match confidence: {result['overall_confidence']:.2%}")

if __name__ == '__main__':
    cli()
```

## Implementation Timeline

### Week 1-2: Foundation
- Set up project structure
- Implement state models
- Create container manager
- Build filesystem monitor
- Basic tool definitions

### Week 3-4: Agents
- Discovery agent
- Platform selection agent
- Installation agent
- Analysis agent
- Generation agent
- Quality check agent

### Week 4-5: Workflow
- LangGraph workflow assembly
- Conditional routing logic
- Checkpointing setup
- Error handling

### Week 5-6: CLI & Integration
- CLI commands
- Configuration management
- Output formatting
- Integration with saigen

### Week 6-7: Testing & Polish
- Unit tests
- Integration tests
- Documentation
- Examples

### Week 8: Release
- Package for PyPI
- Docker image
- Documentation
- Example workflows

## Key Design Decisions

1. **LangGraph for orchestration** - State management, conditional routing, checkpointing
2. **Docker for isolation** - Clean, reproducible test environments
3. **AI for analysis** - LLMs interpret observations and generate saidata
4. **Pydantic for models** - Type safety and validation
5. **Modular agents** - Single responsibility per agent
6. **Confidence scoring** - Quantify reliability
7. **Human-in-the-loop** - Pause for review when confidence is low

## Success Metrics

- **Accuracy**: Generated saidata matches manual verification >90%
- **Coverage**: Supports 10+ platforms
- **Speed**: Complete verification in <5 minutes per platform
- **Confidence**: Average confidence score >0.8
- **Reliability**: <5% failure rate on common software

## Next Steps

1. Review and approve this plan
2. Set up development environment
3. Start with Phase 1 (foundation)
4. Iterate based on learnings
5. Expand to more platforms and software types
