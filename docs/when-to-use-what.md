# When to Use SAI vs SAIGEN

Understanding when to use each tool will help you choose the right installation and workflow for your needs.

## SAI - Software Action Interface

### What It Does
SAI executes software management actions using provider-based configurations and saidata files.

### When to Use SAI

**✅ Use SAI when you need to:**
- Install, configure, or manage software on systems
- Execute automated deployment workflows
- Run software management actions in CI/CD pipelines
- Apply consistent software configurations across environments
- Manage software lifecycle (install, update, remove)
- Work with existing saidata from the saidata repository

**📦 Installation:**
```bash
pip install sai
```

### SAI Use Cases

1. **Production Deployments**
   ```bash
   sai install nginx
   sai configure postgresql --config prod.yaml
   ```

2. **CI/CD Pipelines**
   ```yaml
   # .github/workflows/deploy.yml
   - name: Install dependencies
     run: sai install --from requirements.sai.yaml
   ```

3. **Infrastructure Automation**
   ```bash
   sai apply --config infrastructure.yaml --dry-run
   sai apply --config infrastructure.yaml
   ```

4. **System Administration**
   ```bash
   sai list installed
   sai update --all
   sai remove obsolete-package
   ```

### SAI Characteristics
- **Lightweight**: Minimal dependencies
- **Fast**: Quick installation and execution
- **Stable**: Production-ready
- **Consumer**: Uses existing saidata
- **Runtime**: Designed for execution environments

---

## SAIGEN - SAI Data Generation

### What It Does
SAIGEN generates, validates, and manages software metadata (saidata) files using AI and repository data.

### When to Use SAIGEN

**✅ Use SAIGEN when you need to:**
- Create new saidata files for software packages
- Generate metadata from package repositories
- Validate and test saidata files
- Update existing saidata with new information
- Build software catalogs and inventories
- Contribute to the saidata repository

**📦 Installation:**
```bash
pip install saigen
# Or with AI features
pip install saigen[llm,rag]
```

### SAIGEN Use Cases

1. **Creating New Saidata**
   ```bash
   saigen generate nginx --provider apt
   saigen generate docker --provider brew
   ```

2. **Batch Generation**
   ```bash
   saigen batch generate --from package-list.txt
   saigen batch generate --provider apt --category web-servers
   ```

3. **Validation and Testing**
   ```bash
   saigen validate nginx.yaml
   saigen test nginx.yaml --mcp-server test-server
   ```

4. **Repository Management**
   ```bash
   saigen repo update apt
   saigen repo cache --all
   saigen repo search nginx
   ```

5. **Metadata Updates**
   ```bash
   saigen update nginx.yaml --refresh-urls
   saigen update --all --check-versions
   ```

### SAIGEN Characteristics
- **Feature-rich**: Comprehensive generation capabilities
- **AI-powered**: Uses LLMs for intelligent generation
- **Developer-focused**: Built for metadata creation
- **Producer**: Creates new saidata
- **Development**: Designed for authoring environments

---

## Combined Usage: SAI with Generation Support

### When to Use Both

**✅ Use `sai[generation]` when you need to:**
- Develop and test saidata in the same environment
- Iterate quickly between generation and execution
- Validate saidata by actually running it
- Work on saidata contributions with immediate testing

**📦 Installation:**
```bash
pip install sai[generation]
```

### Combined Workflow Example

```bash
# 1. Generate new saidata
saigen generate myapp --provider apt

# 2. Validate the generated file
saigen validate myapp.yaml

# 3. Test execution with SAI
sai install myapp --dry-run

# 4. Refine and regenerate if needed
saigen update myapp.yaml --add-action configure

# 5. Test again
sai install myapp --dry-run

# 6. Execute for real
sai install myapp
```

---

## Decision Matrix

| Scenario | Tool | Installation |
|----------|------|--------------|
| Deploy software in production | SAI | `pip install sai` |
| CI/CD pipeline execution | SAI | `pip install sai` |
| Create new saidata files | SAIGEN | `pip install saigen` |
| Validate saidata | SAIGEN | `pip install saigen` |
| Contribute to saidata repo | SAIGEN | `pip install saigen[llm]` |
| Local development & testing | Both | `pip install sai[generation]` |
| Full development environment | Both | `pip install saigen[all]` |
| System administration | SAI | `pip install sai` |
| Metadata management | SAIGEN | `pip install saigen` |

---

## Typical User Profiles

### DevOps Engineer (Production)
**Needs:** Execute software deployments reliably
**Uses:** SAI only
```bash
pip install sai
```

### Metadata Contributor
**Needs:** Create and validate saidata files
**Uses:** SAIGEN with AI features
```bash
pip install saigen[llm,rag]
```

### Full-Stack Developer
**Needs:** Both execution and generation for testing
**Uses:** SAI with generation support
```bash
pip install sai[generation]
```

### System Administrator
**Needs:** Manage software across systems
**Uses:** SAI only
```bash
pip install sai
```

### Platform Engineer
**Needs:** Build software catalogs and automation
**Uses:** Both tools separately
```bash
pip install sai saigen
```

---

## Key Differences Summary

| Aspect | SAI | SAIGEN |
|--------|-----|--------|
| **Purpose** | Execute actions | Generate metadata |
| **Role** | Consumer | Producer |
| **Environment** | Production | Development |
| **Dependencies** | Minimal | Comprehensive |
| **Speed** | Fast | Moderate |
| **AI Features** | No | Yes (optional) |
| **Primary Users** | Operators | Contributors |
| **Output** | System changes | YAML files |

---

## Still Not Sure?

**Start with SAI if:**
- You just want to use existing saidata
- You're deploying to production
- You need minimal dependencies

**Start with SAIGEN if:**
- You want to create new saidata
- You're contributing to the project
- You need metadata generation

**Use both if:**
- You're developing saidata
- You need the complete toolkit
- You want maximum flexibility

For more help, see:
- [Installation Guide](./installation.md)
- [SAI CLI Reference](../sai/docs/cli-reference.md)
- [SAIGEN CLI Reference](../saigen/docs/cli-reference.md)
