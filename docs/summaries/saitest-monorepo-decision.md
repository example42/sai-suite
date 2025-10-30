# Saitest Monorepo Decision

## Decision

Saitest will be developed as part of the sai-suite monorepo alongside sai and saigen.

## Date

October 30, 2025

## Context

We're building saitest, an agent-based verification tool that uses LangGraph to install software in containers, observe system changes, and generate validated saidata. The question was whether to create a separate repository or keep it in the existing sai-suite monorepo.

## Decision Rationale

### Keep in Monorepo (Chosen)

**Advantages:**
1. **Shared Domain Models**: Direct access to saidata models, schema validation, and configuration utilities from saigen
2. **Natural Workflow Integration**: Users want `saigen generate` → `saitest verify` → `sai install` in one place
3. **Code Reuse**: No duplication of models, validators, or repository downloaders
4. **Unified Documentation**: Single source for all SAI tools
5. **Easier Development**: No cross-repo dependency management
6. **Consistent Tooling**: Same CI/CD, testing, linting setup

**Handling Concerns:**
- **Heavy Dependencies**: Use optional dependencies in pyproject.toml
  ```bash
  pip install sai-suite[saitest]  # Only install when needed
  ```
- **Experimental Status**: Mark clearly in docs, doesn't affect stable tools
- **Docker Requirement**: Runtime check, not installation requirement

### Alternative Considered: Separate Repository

**Would have provided:**
- Independent evolution
- Cleaner dependency isolation
- Separate release cycle

**But would have cost:**
- Code duplication (saidata models)
- Dependency synchronization overhead
- Fragmented documentation
- Integration friction

## Implementation Details

### Directory Structure
```
sai-suite/
├── sai/          # Stable
├── saigen/       # Stable
├── saitest/      # Experimental - new
├── shared/       # Shared code (if needed)
├── schemas/      # Shared schemas
├── docs/         # General docs
└── tests/
    ├── sai/
    ├── saigen/
    └── saitest/  # New
```

### Documentation Pattern
- **Tool-specific**: `saitest/docs/` (architecture, CLI reference, examples)
- **General**: `docs/` (cross-tool workflows, installation)
- **Summaries**: `docs/summaries/` (this file)

### Dependency Management
```toml
[project.optional-dependencies]
saitest = [
    "langgraph>=0.1",
    "docker>=7.0",
    "watchdog>=3.0",
]
```

### Code Sharing
```python
# Saitest imports from saigen
from saigen.models.saidata import SaidataModel
from saigen.utils.validation import validate_saidata

# Saitest-specific code
from saitest.models.observation import Observation
from saitest.core.state import VerificationState
```

## Migration Path

If saitest grows significantly or needs independent releases (6-12 months):
1. Extract to separate `saitest` repository
2. Create `sai-models` package for shared code
3. Both repos depend on `sai-models`

But starting in monorepo provides maximum flexibility.

## Precedents

Similar projects that use monorepos:
- **LangChain**: langchain, langchain-core, langgraph all in one repo
- **Terraform**: Multiple providers in one repo
- **Kubernetes**: Many tools in one repo

## Status

Approved - Implementation starting with Phase 1 (foundation)
