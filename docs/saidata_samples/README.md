# Saidata Sample Files

This directory contains sample saidata files compliant with the 0.3 schema specification.

## Directory Structure

Samples are organized using a two-letter prefix directory structure:

```
<first-two-letters>/<software-name>/default.yaml
```

For example:
- `ng/nginx/default.yaml` - NGINX web server
- `mo/mongodb/default.yaml` - MongoDB database
- `re/redis/default.yaml` - Redis cache
- `do/docker/default.yaml` - Docker container runtime

## Schema Version

All samples use **version 0.3** of the saidata schema.

## Key Changes from 0.2 to 0.3

### Required Fields
- **packages**: Now requires both `name` (logical name) and `package_name` (actual package name)
  ```yaml
  packages:
    - name: "server"
      package_name: "nginx"
  ```

### New Installation Methods
- **sources**: Source code compilation configurations (see golang, nodejs, python samples)
- **binaries**: Binary download and installation (see golang, nodejs, terraform samples)
- **scripts**: Script-based installation (see golang, nodejs, python samples)

### Enhanced Features
- URL templating with `{{version}}`, `{{platform}}`, `{{architecture}}`
- Checksum validation support
- Enhanced security metadata
- Improved compatibility matrix

## Available Samples

### Infrastructure & Containers
- **do/docker** - Docker container runtime
- **ku/kubernetes** - Kubernetes orchestration

### Databases
- **el/elasticsearch** - Elasticsearch search engine
- **mo/mongodb** - MongoDB NoSQL database
- **my/mysql** - MySQL relational database
- **re/redis** - Redis in-memory database

### Web Servers & Proxies
- **ng/nginx** - NGINX web server

### Monitoring & Observability
- **gr/grafana** - Grafana visualization platform
- **pr/prometheus** - Prometheus monitoring

### CI/CD & DevOps
- **je/jenkins** - Jenkins CI/CD server
- **te/terraform** - Terraform IaC tool

### Programming Languages & Runtimes
- **go/golang** - Go programming language (showcases sources, binaries, scripts)
- **no/nodejs** - Node.js JavaScript runtime (showcases sources, binaries, scripts)
- **py/python** - Python programming language (showcases sources, scripts)

## Usage

These samples can be used as:
1. **Reference examples** for creating new saidata files
2. **RAG training data** for AI-powered generation
3. **Validation test cases** for schema compliance
4. **Documentation** for saidata structure

## Validation

Validate any sample file:
```bash
saigen validate docs/saidata_samples/ng/nginx/default.yaml
```

## Generation

Use samples as context for generating new saidata:
```bash
saigen generate <software-name>
```

The RAG system will automatically use these samples to improve generation quality.
