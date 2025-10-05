# Docker Test Environments

Docker images for testing saidata files across different operating systems and package managers.

## Available Images

- `test-ubuntu` - Ubuntu 24.04 with apt
- `test-debian` - Debian 12 with apt
- `test-fedora` - Fedora 40 with dnf
- `test-alpine` - Alpine 3.19 with apk

## Building Images

Build all images:
```bash
make docker-build-test
```

Build specific image:
```bash
docker build -t sai-test-ubuntu docker/test-ubuntu/
```

## Using Images

Test a saidata file:
```bash
docker run --rm -v $(pwd):/data sai-test-ubuntu saigen test-system /data/nginx.yaml
```

Test with real installation (requires privileged mode):
```bash
docker run --rm --privileged -v $(pwd):/data sai-test-ubuntu \
  saigen test-system --real-install /data/nginx.yaml
```

Batch test all files in a directory:
```bash
docker run --rm -v $(pwd)/packages:/data sai-test-ubuntu \
  saigen test-system --batch /data
```

## Publishing Images

Images should be published to GitHub Container Registry:

```bash
# Tag images
docker tag sai-test-ubuntu ghcr.io/example42/sai-test-ubuntu:latest
docker tag sai-test-debian ghcr.io/example42/sai-test-debian:latest
docker tag sai-test-fedora ghcr.io/example42/sai-test-fedora:latest
docker tag sai-test-alpine ghcr.io/example42/sai-test-alpine:latest

# Push images
docker push ghcr.io/example42/sai-test-ubuntu:latest
docker push ghcr.io/example42/sai-test-debian:latest
docker push ghcr.io/example42/sai-test-fedora:latest
docker push ghcr.io/example42/sai-test-alpine:latest
```

## CI/CD Integration

These images are used in GitHub Actions workflows for automated testing.
See `.github/workflows/test-saidata.yml` in the saidata repository.
