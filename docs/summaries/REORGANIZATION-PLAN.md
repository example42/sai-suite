# Documentation Reorganization Plan

## Current State
Docs are mixed together - SAI-specific, SAIGEN-specific, and general docs all in one place.

## New Structure

```
docs/                           # General/shared documentation
├── installation.md            # Keep - general installation
├── when-to-use-what.md        # Keep - decision guide
├── MIGRATION.md               # Keep - migration guide
├── architecture-diagram.md    # Keep - overall architecture
├── summaries/                 # Keep - implementation summaries
└── README.md                  # New - docs index

sai/docs/                      # SAI-specific documentation
├── cli-reference.md
├── configuration-guide.md
├── sai-apply-command.md
├── template-engine.md
└── examples/
    └── sai-config-sample.yaml

saigen/docs/                   # SAIGEN-specific documentation
├── cli-reference.md
├── configuration-guide.md
├── repository-management.md
├── repository-configuration.md
├── repository-troubleshooting.md
├── generation-engine.md
├── generation-logging.md
├── rag-indexing-guide.md
├── testing-guide.md
├── url-features.md
└── examples/
    ├── saigen-config-sample.yaml
    ├── saidata_samples/
    └── software_lists/
```

## Files to Move

### To sai/docs/
- sai-apply-command.md
- template-engine-implementation.md
- sai-config-sample.yaml
- specialized-providers-roadmap.md (SAI providers)

### To saigen/docs/
- repository-configuration.md
- repository-management.md
- repository-troubleshooting.md
- repository-parser-improvements.md
- generation-engine-best-practices.md
- generation-logging.md
- rag-indexing-guide.md
- testing-guide.md
- TESTING-QUICKSTART.md
- refresh-versions-*.md
- retry-generation-feature.md
- stats-command.md
- url-*.md
- URL-FEATURE-README.md
- saigen-config-sample.yaml
- saidata_samples/
- software_lists/

### To Keep in docs/ (General)
- installation.md (updated for monorepo)
- when-to-use-what.md (decision guide)
- MIGRATION.md (migration guide)
- architecture-diagram.md (overall architecture)
- summaries/ (implementation summaries)

### To Remove/Archive (Obsolete)
- cli-reference-0.3.md (old version)
- command-reference.md (duplicate)
- configuration-samples.md (use examples instead)
- SAIDATA_0.3_FEATURES.md (old version)
- saidata-0.3-migration-guide.md (old version)
- hierarchical-saidata-structure.md (outdated)
- output-formatting-improvements.md (implementation detail)
- project-structure.md (replaced by MONOREPO.md)
- TODO/ (move to GitHub issues)

### To Consolidate
- api-reference.md → Split into sai/docs/ and saigen/docs/
- configuration-guide.md → Split into sai/docs/ and saigen/docs/
- troubleshooting.md → Split into sai/docs/ and saigen/docs/
