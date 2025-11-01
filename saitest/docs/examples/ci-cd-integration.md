# CI/CD Integration Example

This example demonstrates how to integrate saitest into CI/CD pipelines for automated saidata generation and validation.

## Why CI/CD Integration?

- **Automated verification**: Generate saidata automatically on changes
- **Quality gates**: Ensure saidata meets quality standards
- **Continuous validation**: Test saidata against actual installations
- **Version tracking**: Track saidata changes over time

## GitHub Actions

### Basic Workflow

**.github/workflows/verify-saidata.yml:**

```yaml
name: Verify Saidata

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  verify:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install saitest
        run: |
          pip install sai-suite[saitest]
      
      - name: Verify saidata
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          saitest verify nginx \
            --platforms ubuntu:22.04,debian:12 \
            --output-dir ./saidata \
            --verbose
      
      - name: Upload saidata
        uses: actions/upload-artifact@v3
        with:
          name: saidata
          path: ./saidata/
```

### Test Existing Saidata

**.github/workflows/test-saidata.yml:**

```yaml
name: Test Saidata

on:
  push:
    paths:
      - 'software/**/*.yaml'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install saitest
        run: pip install sai-suite[saitest]
      
      - name: Test changed saidata files
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          # Get changed files
          git diff --name-only ${{ github.event.before }} ${{ github.sha }} \
            | grep '\.yaml$' \
            | while read file; do
              echo "Testing $file..."
              saitest test "$file" --verbose
            done
```

### Multi-Platform Matrix

**.github/workflows/multi-platform-verify.yml:**

```yaml
name: Multi-Platform Verification

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        software: [nginx, apache, postgresql, redis, mysql]
        platforms:
          - ubuntu:22.04,debian:12
          - rockylinux:9,fedora:40
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install saitest
        run: pip install sai-suite[saitest]
      
      - name: Verify ${{ matrix.software }}
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          saitest verify ${{ matrix.software }} \
            --platforms ${{ matrix.platforms }} \
            --output-dir ./saidata \
            --verbose
      
      - name: Check confidence
        run: |
          # Parse confidence from output
          # Fail if confidence < 0.8
          python scripts/check_confidence.py ./saidata/${{ matrix.software }}/
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: saidata-${{ matrix.software }}
          path: ./saidata/${{ matrix.software }}/
```

### Quality Gate

**.github/workflows/quality-gate.yml:**

```yaml
name: Saidata Quality Gate

on:
  pull_request:
    paths:
      - 'software/**/*.yaml'

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install saitest
        run: pip install sai-suite[saitest]
      
      - name: Verify and check quality
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          # Get changed software
          CHANGED_SOFTWARE=$(git diff --name-only origin/main... \
            | grep 'software/' \
            | cut -d'/' -f2 \
            | sort -u)
          
          for software in $CHANGED_SOFTWARE; do
            echo "Verifying $software..."
            
            # Run verification
            saitest verify "$software" \
              --platforms ubuntu:22.04,debian:12 \
              --output-dir ./verified \
              --verbose
            
            # Check confidence
            CONFIDENCE=$(python scripts/get_confidence.py ./verified/$software/)
            
            if (( $(echo "$CONFIDENCE < 0.8" | bc -l) )); then
              echo "❌ Low confidence ($CONFIDENCE) for $software"
              exit 1
            else
              echo "✅ High confidence ($CONFIDENCE) for $software"
            fi
          done
      
      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Saidata quality check passed!'
            })
```

## GitLab CI

### Basic Pipeline

**.gitlab-ci.yml:**

```yaml
stages:
  - verify
  - test
  - deploy

verify-saidata:
  stage: verify
  image: python:3.10
  before_script:
    - pip install sai-suite[saitest]
  script:
    - |
      saitest verify nginx \
        --platforms ubuntu:22.04,debian:12 \
        --output-dir ./saidata \
        --verbose
  artifacts:
    paths:
      - saidata/
    expire_in: 1 week
  only:
    - main
    - develop

test-saidata:
  stage: test
  image: python:3.10
  before_script:
    - pip install sai-suite[saitest]
  script:
    - |
      for file in software/**/*.yaml; do
        echo "Testing $file..."
        saitest test "$file" --verbose
      done
  only:
    changes:
      - software/**/*.yaml
```

### Multi-Platform Pipeline

**.gitlab-ci.yml:**

```yaml
.verify-template: &verify-template
  stage: verify
  image: python:3.10
  before_script:
    - pip install sai-suite[saitest]
  script:
    - |
      saitest verify $SOFTWARE \
        --platforms $PLATFORMS \
        --output-dir ./saidata \
        --verbose
  artifacts:
    paths:
      - saidata/

verify-nginx-debian:
  <<: *verify-template
  variables:
    SOFTWARE: nginx
    PLATFORMS: ubuntu:22.04,debian:12

verify-nginx-rhel:
  <<: *verify-template
  variables:
    SOFTWARE: nginx
    PLATFORMS: rockylinux:9,fedora:40

verify-apache:
  <<: *verify-template
  variables:
    SOFTWARE: apache
    PLATFORMS: ubuntu:22.04,debian:12
```

## Jenkins

### Jenkinsfile

```groovy
pipeline {
    agent any
    
    environment {
        OPENAI_API_KEY = credentials('openai-api-key')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install sai-suite[saitest]'
            }
        }
        
        stage('Verify Saidata') {
            steps {
                sh '''
                    saitest verify nginx \
                        --platforms ubuntu:22.04,debian:12 \
                        --output-dir ./saidata \
                        --verbose
                '''
            }
        }
        
        stage('Test Saidata') {
            steps {
                sh '''
                    for file in software/**/*.yaml; do
                        echo "Testing $file..."
                        saitest test "$file" --verbose
                    done
                '''
            }
        }
        
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: 'saidata/**/*.yaml'
            }
        }
    }
    
    post {
        failure {
            mail to: 'team@example.com',
                 subject: "Saidata verification failed: ${env.JOB_NAME}",
                 body: "Check ${env.BUILD_URL}"
        }
    }
}
```

### Parallel Verification

```groovy
pipeline {
    agent any
    
    stages {
        stage('Verify Multiple Software') {
            parallel {
                stage('Nginx') {
                    steps {
                        sh 'saitest verify nginx --platforms ubuntu:22.04,debian:12 --output-dir ./saidata'
                    }
                }
                stage('Apache') {
                    steps {
                        sh 'saitest verify apache --platforms ubuntu:22.04,debian:12 --output-dir ./saidata'
                    }
                }
                stage('PostgreSQL') {
                    steps {
                        sh 'saitest verify postgresql --platforms ubuntu:22.04,debian:12 --output-dir ./saidata'
                    }
                }
            }
        }
    }
}
```

## CircleCI

**.circleci/config.yml:**

```yaml
version: 2.1

jobs:
  verify-saidata:
    docker:
      - image: cimg/python:3.10
    steps:
      - checkout
      - run:
          name: Install saitest
          command: pip install sai-suite[saitest]
      - run:
          name: Verify saidata
          command: |
            saitest verify nginx \
              --platforms ubuntu:22.04,debian:12 \
              --output-dir ./saidata \
              --verbose
      - store_artifacts:
          path: ./saidata
      - persist_to_workspace:
          root: .
          paths:
            - saidata

  test-saidata:
    docker:
      - image: cimg/python:3.10
    steps:
      - checkout
      - run:
          name: Install saitest
          command: pip install sai-suite[saitest]
      - run:
          name: Test saidata
          command: |
            for file in software/**/*.yaml; do
              saitest test "$file" --verbose
            done

workflows:
  verify-and-test:
    jobs:
      - verify-saidata
      - test-saidata:
          requires:
            - verify-saidata
```

## Automated Scripts

### Batch Verification Script

**scripts/verify-all.sh:**

```bash
#!/bin/bash
set -e

SOFTWARE_LIST="nginx apache postgresql redis mysql"
PLATFORMS="ubuntu:22.04,debian:12"
OUTPUT_DIR="./saidata"
MIN_CONFIDENCE=0.8

echo "Starting batch verification..."

for software in $SOFTWARE_LIST; do
  echo ""
  echo "========================================="
  echo "Verifying $software..."
  echo "========================================="
  
  # Run verification
  saitest verify "$software" \
    --platforms "$PLATFORMS" \
    --output-dir "$OUTPUT_DIR" \
    --verbose
  
  # Check exit code
  if [ $? -ne 0 ]; then
    echo "❌ Verification failed for $software"
    exit 1
  fi
  
  # Check confidence (requires custom script)
  CONFIDENCE=$(python scripts/get_confidence.py "$OUTPUT_DIR/$software/")
  
  if (( $(echo "$CONFIDENCE < $MIN_CONFIDENCE" | bc -l) )); then
    echo "⚠️  Low confidence ($CONFIDENCE) for $software"
    echo "   Manual review required"
  else
    echo "✅ High confidence ($CONFIDENCE) for $software"
  fi
done

echo ""
echo "Batch verification complete!"
```

### Confidence Checker Script

**scripts/check_confidence.py:**

```python
#!/usr/bin/env python3
import sys
import yaml
from pathlib import Path

def check_confidence(saidata_dir):
    """Check confidence score from saidata metadata"""
    default_file = Path(saidata_dir) / "default.yaml"
    
    if not default_file.exists():
        print(f"Error: {default_file} not found")
        sys.exit(1)
    
    with open(default_file) as f:
        saidata = yaml.safe_load(f)
    
    # Check for confidence in metadata (if saitest adds it)
    confidence = saidata.get('metadata', {}).get('confidence', 0.0)
    
    print(f"Confidence: {confidence}")
    
    if confidence < 0.8:
        print("❌ Low confidence - manual review required")
        sys.exit(1)
    else:
        print("✅ High confidence")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: check_confidence.py <saidata_dir>")
        sys.exit(1)
    
    check_confidence(sys.argv[1])
```

### Scheduled Verification

**scripts/scheduled-verify.sh:**

```bash
#!/bin/bash
# Run via cron: 0 0 * * 0 /path/to/scheduled-verify.sh

set -e

# Configuration
REPO_DIR="/path/to/saidata-repo"
OUTPUT_DIR="$REPO_DIR/software"
PLATFORMS="ubuntu:22.04,debian:12,rockylinux:9"
BRANCH="automated-updates"

cd "$REPO_DIR"

# Create branch
git checkout -b "$BRANCH" || git checkout "$BRANCH"
git pull origin main

# Get list of software to verify
SOFTWARE_LIST=$(ls "$OUTPUT_DIR" | grep -v '\.yaml$')

# Verify each
for software in $SOFTWARE_LIST; do
  echo "Verifying $software..."
  
  saitest verify "$software" \
    --platforms "$PLATFORMS" \
    --output-dir "$OUTPUT_DIR" \
    --verbose
done

# Commit changes
git add "$OUTPUT_DIR"
git commit -m "Automated saidata update $(date +%Y-%m-%d)"
git push origin "$BRANCH"

# Create PR (using gh CLI)
gh pr create \
  --title "Automated saidata update $(date +%Y-%m-%d)" \
  --body "Automated verification and update of saidata files" \
  --base main \
  --head "$BRANCH"
```

## Docker Integration

### Dockerfile for CI

**Dockerfile.ci:**

```dockerfile
FROM python:3.10-slim

# Install Docker CLI for container management
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*

# Install saitest
RUN pip install sai-suite[saitest]

# Set working directory
WORKDIR /workspace

# Default command
CMD ["saitest", "--help"]
```

### Docker Compose for Testing

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  saitest:
    build:
      context: .
      dockerfile: Dockerfile.ci
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./saidata:/workspace/saidata
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    command: >
      saitest verify nginx
      --platforms ubuntu:22.04,debian:12
      --output-dir /workspace/saidata
      --verbose
```

## Best Practices

### 1. Use Secrets Management

```yaml
# GitHub Actions
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

# GitLab CI
variables:
  OPENAI_API_KEY: $CI_OPENAI_API_KEY
```

### 2. Cache Dependencies

```yaml
# GitHub Actions
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### 3. Parallel Execution

```yaml
# GitHub Actions matrix
strategy:
  matrix:
    software: [nginx, apache, postgresql]
```

### 4. Quality Gates

```bash
# Fail if confidence < 0.8
if [ $CONFIDENCE -lt 0.8 ]; then
  exit 1
fi
```

### 5. Artifact Storage

```yaml
# Store generated saidata
- uses: actions/upload-artifact@v3
  with:
    name: saidata
    path: ./saidata/
```

## Monitoring and Notifications

### Slack Notifications

```yaml
# GitHub Actions
- name: Notify Slack
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Saidata verification failed for ${{ github.repository }}"
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Email Notifications

```groovy
// Jenkins
post {
    failure {
        mail to: 'team@example.com',
             subject: "Saidata verification failed",
             body: "Check ${env.BUILD_URL}"
    }
}
```

## Next Steps

- [Basic Verification](basic-verification.md) - Simple verification workflow
- [Multi-Platform Testing](multi-platform-testing.md) - Test across platforms
- [CLI Reference](../cli-reference.md) - Complete command documentation
- [Architecture](../architecture.md) - Design details
