# Build a binary distributable out of ia-code-review
FROM quay.io/automotive-toolchain/python3-uv:latest as builder
WORKDIR /code
COPY pyproject.toml uv.lock README.md ./
COPY src src
RUN uv build --no-cache

# Use the binary distributable in the system Python environment
# so it's accessible globally in containers
FROM registry.access.redhat.com/ubi9:latest
ENV DNF_OPTS="--setopt=install_weak_deps=False --setopt=tsflags=nodocs"
RUN dnf install -y \
                python3.12-pip \
 && dnf clean all -y
COPY --from=builder /code/dist/*.whl /tmp/
RUN pip3.12 install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl
