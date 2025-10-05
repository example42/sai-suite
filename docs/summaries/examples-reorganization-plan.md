# Examples Directory Reorganization Plan

**Date:** May 10, 2025

## Current State

The `examples/` directory contains a mix of:
- Demo scripts (Python files)
- Configuration examples (YAML/JSON)
- Testing examples
- CI/CD examples
- Old version examples (0.3)
- Documentation files

## Issues

1. **Mixed content** - Scripts, configs, and docs all together
2. **Unclear ownership** - Not clear if examples are for SAI or SAIGEN
3. **Old versions** - saidata-0.3-examples are outdated
4. **Development scripts** - Demo scripts should be in scripts/development/
5. **Documentation** - Some .md files should be in docs/

## New Structure

```
examples/                          # Root examples (general/shared only)
├── README.md                     # Examples index
└── ci-cd/                        # CI/CD examples (shared)
    ├── github-actions-test-saidata.yml
    └── gitlab-ci-test-saidata.yml

sai/docs/examples/                # SAI-specific examples
├── action-files/                 # Action file examples
│   ├── simple.yaml
│   ├── flexible.yaml
│   ├── extra-params.yaml
│   └── README.md
└── sai-config-sample.yaml       # Already there

saigen/docs/examples/             # SAIGEN-specific examples
├── repository-configs/           # Repository configurations
│   ├── comprehensive-example.yaml
│   └── README.md
├── saidata-samples/             # Already there
├── software_lists/              # Already there
├── testing/                     # Testing examples
│   ├── nginx-example.yaml
│   ├── python-example.yaml
│   ├── test-docker.sh
│   ├── test-local.sh
│   └── README.md
└── saigen-config-sample.yaml    # Already there

scripts/development/              # Development/demo scripts
├── sai/                         # SAI demo scripts
│   ├── execution_engine_demo.py
│   ├── saidata_loader_demo.py
│   ├── template_engine_demo.py
│   └── security_demo.py
└── saigen/                      # SAIGEN demo scripts
    ├── generation_engine_demo.py
    ├── llm_provider_demo.py
    ├── advanced_validation_demo.py
    ├── retry_generation_example.py
    ├── saidata_validation_demo.py
    ├── output_formatting_demo.py
    └── sample_data_demo.py

docs/archive/examples/            # Obsolete examples
└── saidata-0.3-examples/        # Old version examples
```

## Actions

### Move to `sai/docs/examples/`
- action-file-*.yaml → action-files/
- Create action-files/README.md

### Move to `saigen/docs/examples/`
- repository-configs/ (already has comprehensive-example.yaml)
- testing/ (nginx, python examples, test scripts)
- repository-config.yaml → repository-configs/

### Move to `scripts/development/sai/`
- execution_engine_demo.py
- saidata_loader_demo.py
- template_engine_demo.py
- security_demo.py
- hierarchical_saidata_demo.py

### Move to `scripts/development/saigen/`
- generation_engine_demo.py
- llm_provider_demo.py
- advanced_validation_demo.py
- retry_generation_example.py
- saidata_validation_demo.py
- output_formatting_demo.py
- sample_data_demo.py

### Move to `docs/archive/examples/`
- saidata-0.3-examples/ (old version)
- saidata-repo/ (outdated testing setup)
- generation_logging_example.md (implementation detail)

### Keep in `examples/` (shared)
- ci-cd/ (CI/CD examples are shared)
- README.md (new index file)

## Benefits

✅ **Clear separation** - SAI vs SAIGEN examples  
✅ **Proper location** - Demo scripts in scripts/development/  
✅ **Better organization** - Examples with their docs  
✅ **Easy to find** - Logical structure  
✅ **Maintainable** - Update examples with code  
