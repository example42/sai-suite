# Documentation Quick Reference

## 📍 Where to Find What

### Getting Started
| What | Where |
|------|-------|
| Quick start | [QUICK-START.md](QUICK-START.md) |
| Choose SAI or SAIGEN | [docs/when-to-use-what.md](docs/when-to-use-what.md) |
| Installation | [docs/installation.md](docs/installation.md) |
| Architecture | [docs/architecture-diagram.md](docs/architecture-diagram.md) |

### Using SAI
| What | Where |
|------|-------|
| SAI overview | [sai/README.md](sai/README.md) |
| CLI reference | [sai/docs/cli-reference.md](sai/docs/cli-reference.md) |
| Apply command | [sai/docs/sai-apply-command.md](sai/docs/sai-apply-command.md) |
| Template engine | [sai/docs/template-engine.md](sai/docs/template-engine.md) |
| Examples | [sai/docs/examples/](sai/docs/examples/) |

### Using SAIGEN
| What | Where |
|------|-------|
| SAIGEN overview | [saigen/README.md](saigen/README.md) |
| CLI reference | [saigen/docs/cli-reference.md](saigen/docs/cli-reference.md) |
| Configuration | [saigen/docs/configuration-guide.md](saigen/docs/configuration-guide.md) |
| Generation engine | [saigen/docs/generation-engine.md](saigen/docs/generation-engine.md) |
| Testing | [saigen/docs/testing-guide.md](saigen/docs/testing-guide.md) |
| Repository management | [saigen/docs/repository-management.md](saigen/docs/repository-management.md) |
| Examples | [saigen/docs/examples/](saigen/docs/examples/) |

### Development
| What | Where |
|------|-------|
| Monorepo structure | [MONOREPO.md](MONOREPO.md) |
| Implementation details | [docs/summaries/](docs/summaries/) |
| Release process | [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md) |

## 📂 Directory Structure

```
sai-python/
├── docs/                      # General documentation
│   ├── README.md             # Documentation index
│   ├── installation.md       # Installation guide
│   ├── when-to-use-what.md   # Decision guide
│   ├── MIGRATION.md          # Migration guide
│   ├── architecture-diagram.md
│   ├── summaries/            # Implementation summaries
│   └── archive/              # Obsolete docs
│
├── sai/docs/                 # SAI-specific docs
│   ├── README.md
│   ├── cli-reference.md
│   ├── sai-apply-command.md
│   ├── template-engine.md
│   └── examples/
│
└── saigen/docs/              # SAIGEN-specific docs
    ├── README.md
    ├── cli-reference.md
    ├── configuration-guide.md
    ├── generation-engine.md
    ├── testing-guide.md
    ├── repository-management.md
    └── examples/
```

## 🔍 Common Questions

### "Which tool should I use?"
→ [docs/when-to-use-what.md](docs/when-to-use-what.md)

### "How do I install?"
→ [docs/installation.md](docs/installation.md)

### "How do I use SAI commands?"
→ [sai/docs/cli-reference.md](sai/docs/cli-reference.md)

### "How do I generate saidata?"
→ [saigen/docs/cli-reference.md](saigen/docs/cli-reference.md)

### "How do I configure SAIGEN?"
→ [saigen/docs/configuration-guide.md](saigen/docs/configuration-guide.md)

### "How do I test saidata?"
→ [saigen/docs/testing-guide.md](saigen/docs/testing-guide.md)

### "How does the monorepo work?"
→ [MONOREPO.md](MONOREPO.md)

### "How do I contribute?"
→ [MONOREPO.md](MONOREPO.md) (Development section)

## 📊 Statistics

- **General docs**: 6 files
- **SAI docs**: 5 files
- **SAIGEN docs**: 23 files
- **Total**: 47 organized files

## 🎯 Quick Navigation

Start here based on your role:

**End User (SAI):**
1. [When to Use What](docs/when-to-use-what.md)
2. [Installation](docs/installation.md)
3. [SAI CLI Reference](sai/docs/cli-reference.md)

**End User (SAIGEN):**
1. [When to Use What](docs/when-to-use-what.md)
2. [Installation](docs/installation.md)
3. [SAIGEN CLI Reference](saigen/docs/cli-reference.md)

**Developer:**
1. [Quick Start](QUICK-START.md)
2. [Monorepo Structure](MONOREPO.md)
3. [Implementation Summaries](docs/summaries/)

**Contributor:**
1. [Monorepo Structure](MONOREPO.md)
2. [SAIGEN Generation Engine](saigen/docs/generation-engine.md)
3. [Testing Guide](saigen/docs/testing-guide.md)
