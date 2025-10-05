# SAI Monorepo Architecture

## Package Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SAI Python Monorepo                      │
│                  github.com/example42/sai-python            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│      SAI Package          │   │    SAIGEN Package         │
│   (Execution Runtime)     │   │  (Generation Tool)        │
├───────────────────────────┤   ├───────────────────────────┤
│ pip install sai           │   │ pip install saigen        │
│                           │   │                           │
│ Features:                 │   │ Features:                 │
│ • Execute actions         │   │ • Generate saidata        │
│ • Provider system         │   │ • Validate metadata       │
│ • Multi-platform          │   │ • Repository integration  │
│ • Dry-run mode            │   │ • AI-powered generation   │
│                           │   │ • Batch processing        │
│ Dependencies: Minimal     │   │ Dependencies: Full        │
│ Size: ~10 packages        │   │ Size: ~20+ packages       │
└───────────────────────────┘   └───────────────────────────┘
                │                           │
                │                           │
                └─────────────┬─────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │   Shared Components     │
                ├─────────────────────────┤
                │ • Common models         │
                │ • Utilities             │
                │ • Test fixtures         │
                │ • Documentation         │
                └─────────────────────────┘
```

## Installation Options

```
┌─────────────────────────────────────────────────────────────┐
│                    Installation Choices                     │
└─────────────────────────────────────────────────────────────┘

Option 1: SAI Only (Lightweight)
┌──────────────────────┐
│  pip install sai     │  →  SAI package only
└──────────────────────┘      • Minimal dependencies
                              • Fast installation
                              • Production ready

Option 2: SAIGEN Only
┌──────────────────────┐
│  pip install saigen  │  →  SAIGEN package only
└──────────────────────┘      • Generation features
                              • Repository support
                              • Validation tools

Option 3: SAI with Generation
┌────────────────────────────┐
│  pip install sai[generation] │  →  SAI + SAIGEN
└────────────────────────────┘      • Both tools
                                    • Unified install
                                    • Development use

Option 4: SAIGEN with AI
┌──────────────────────────┐
│  pip install saigen[llm] │  →  SAIGEN + AI providers
└──────────────────────────┘      • OpenAI support
                                  • Anthropic support
                                  • AI generation

Option 5: Everything
┌──────────────────────────┐
│  pip install saigen[all] │  →  All features
└──────────────────────────┘      • LLM support
                                  • RAG support
                                  • Full toolkit
```

## User Journey Map

```
┌─────────────────────────────────────────────────────────────┐
│                      User Personas                          │
└─────────────────────────────────────────────────────────────┘

DevOps Engineer (Production)
    │
    ├─ Need: Execute deployments
    ├─ Install: pip install sai
    └─ Use: sai install nginx
        └─ Result: Software deployed ✓

Metadata Contributor
    │
    ├─ Need: Create saidata
    ├─ Install: pip install saigen[llm]
    └─ Use: saigen generate nginx
        └─ Result: YAML file created ✓

Full-Stack Developer
    │
    ├─ Need: Both execution and generation
    ├─ Install: pip install sai[generation]
    └─ Use: saigen generate → sai install
        └─ Result: End-to-end workflow ✓

System Administrator
    │
    ├─ Need: Manage software
    ├─ Install: pip install sai
    └─ Use: sai list, sai update
        └─ Result: Systems managed ✓
```

## Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Dependency Layers                        │
└─────────────────────────────────────────────────────────────┘

Layer 1: Core (Both packages)
┌─────────────────────────────────────────────────────────────┐
│ pydantic • click • pyyaml • httpx • rich • jsonschema       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
Layer 2: SAI Specific
┌─────────────────────────────────────────────────────────────┐
│ jinja2 • packaging                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
Layer 3: SAIGEN Specific
┌─────────────────────────────────────────────────────────────┐
│ aiohttp • aiofiles                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
Layer 4: Optional (SAIGEN)
┌─────────────────────────────────────────────────────────────┐
│ [llm]: openai • anthropic                                   │
│ [rag]: sentence-transformers • faiss-cpu • numpy            │
└─────────────────────────────────────────────────────────────┘
```

## Build and Release Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  Build and Release Process                  │
└─────────────────────────────────────────────────────────────┘

Development
    │
    ├─ Code changes in sai/ or saigen/
    ├─ Run tests: make test
    ├─ Format: make format
    └─ Lint: make lint
        │
        ▼
Build
    │
    ├─ make build
    │   ├─ Build sai package
    │   └─ Build saigen package
    └─ Artifacts in dist/
        │
        ▼
Test Release
    │
    ├─ make publish-test
    │   ├─ Publish to TestPyPI
    │   └─ Verify installation
    └─ Test in staging
        │
        ▼
Production Release
    │
    ├─ Create git tag (v0.1.0)
    ├─ GitHub Actions triggered
    │   ├─ Build both packages
    │   ├─ Run tests
    │   └─ Publish to PyPI
    └─ Packages available
        │
        ▼
Users Install
    │
    ├─ pip install sai
    └─ pip install saigen
```

## Development Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   Development Workflow                      │
└─────────────────────────────────────────────────────────────┘

1. Clone Repository
   git clone https://github.com/example42/sai-python.git
   cd sai-python
        │
        ▼
2. Setup Environment
   python -m venv .venv
   source .venv/bin/activate
        │
        ▼
3. Install Packages
   make install-both
   (or ./scripts/install-local.sh both)
        │
        ▼
4. Make Changes
   Edit files in sai/ or saigen/
        │
        ▼
5. Test Changes
   make test
   (or pytest tests/)
        │
        ▼
6. Format and Lint
   make format
   make lint
        │
        ▼
7. Build Packages
   make build
        │
        ▼
8. Commit and Push
   git commit -m "..."
   git push
        │
        ▼
9. CI/CD Runs
   GitHub Actions tests and builds
```

## File Organization

```
sai-python/
│
├── sai/                    ← SAI Package
│   ├── sai/               ← Source code
│   │   ├── cli/          ← Command-line interface
│   │   ├── core/         ← Core execution engine
│   │   ├── models/       ← Data models
│   │   ├── providers/    ← Provider system
│   │   └── utils/        ← Utilities
│   ├── pyproject.toml    ← SAI configuration
│   └── README.md         ← SAI documentation
│
├── saigen/                ← SAIGEN Package
│   ├── saigen/           ← Source code
│   │   ├── cli/          ← Command-line interface
│   │   ├── core/         ← Generation engine
│   │   ├── llm/          ← LLM providers
│   │   ├── models/       ← Data models
│   │   ├── repositories/ ← Repository integrations
│   │   └── utils/        ← Utilities
│   ├── pyproject.toml    ← SAIGEN configuration
│   └── README.md         ← SAIGEN documentation
│
├── tests/                 ← Shared tests
│   ├── sai/              ← SAI tests
│   └── saigen/           ← SAIGEN tests
│
├── docs/                  ← Documentation
│   ├── when-to-use-what.md
│   ├── installation.md
│   ├── MIGRATION.md
│   └── summaries/
│
├── scripts/               ← Build scripts
│   ├── build-packages.sh
│   ├── publish-packages.sh
│   └── install-local.sh
│
├── .github/               ← CI/CD
│   └── workflows/
│       ├── build-and-test.yml
│       └── publish.yml
│
├── pyproject.toml         ← Workspace config
├── Makefile               ← Development commands
├── MONOREPO.md            ← Architecture docs
├── QUICK-START.md         ← Quick reference
└── README.md              ← Main README
```

## Decision Tree

```
                    Need SAI tools?
                          │
                          │
            ┌─────────────┴─────────────┐
            │                           │
            ▼                           ▼
    Only execution?              Only generation?
            │                           │
            │                           │
            ▼                           ▼
    pip install sai          pip install saigen
            │                           │
            │                           │
            ▼                           ▼
    Use existing saidata      Create new saidata
            │                           │
            │                           │
            ▼                           ▼
    Production ready ✓        Need AI features?
                                       │
                                       │
                         ┌─────────────┴─────────────┐
                         │                           │
                         ▼                           ▼
                        Yes                         No
                         │                           │
                         │                           │
                         ▼                           ▼
              pip install saigen[llm]    pip install saigen
                         │                           │
                         │                           │
                         ▼                           ▼
              AI-powered generation ✓    Basic generation ✓


    Need both execution and generation?
                    │
                    │
                    ▼
        pip install sai[generation]
                    │
                    │
                    ▼
        Full development toolkit ✓
```

## Summary

The SAI monorepo provides:

- **Two independent packages** (SAI and SAIGEN)
- **Flexible installation** (choose what you need)
- **Shared infrastructure** (tests, docs, CI/CD)
- **Clear separation** (execution vs generation)
- **Easy development** (unified tooling)

Choose your path based on your needs, and the architecture supports you!
