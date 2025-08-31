# User Guide: AI Code Review

Simple guide to get AI-powered code reviews for your GitLab Merge Requests.

## 🚀 Quick Setup Options

### Option 1: Using Pre-built Container (Recommended)

Add this job to your `.gitlab-ci.yml`:

```yaml
stages:
  - test
  - review

ai-code-review:
  stage: review
  image: registry.gitlab.com/juanjeojeda/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY   # Set as protected/masked variable
  script:
    - ai-code-review --post
  allow_failure: true  # Don't block MRs if review fails
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

**Setup Requirements:**

1. **Create GitLab Personal Access Token:**
   - Go to GitLab → **Settings → Access Tokens**
   - Create token with scope: `api`
   - Copy the generated token (starts with `glpat_`)

2. **Configure CI/CD Variables:**
   - In your project: **Settings → CI/CD → Variables**
   - Add `GITLAB_TOKEN` as **Protected + Masked** variable (your GitLab token)
   - Add `GEMINI_API_KEY` as **Protected + Masked** variable
   - Get your Gemini key from: <https://makersuite.google.com/app/apikey>

### Option 2: Build Your Own Container

Create your own container and publish to your registry:

#### 2.1. Use Project's Containerfile

Use the existing `Containerfile` from the project:

```dockerfile
# Build a binary distributable out of ai-code-review
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
```

#### 2.2. Build and Push

```bash
# Build container
podman build -t $CI_REGISTRY_IMAGE/ai-review:latest .

# Push to your registry
podman push $CI_REGISTRY_IMAGE/ai-review:latest
```

#### 2.3. Use in CI/CD

```yaml
ai-code-review:
  stage: review
  image: $CI_REGISTRY_IMAGE/ai-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Option 3: Install from GitLab Repository

Install directly from the GitLab repository in your CI job:

```yaml
ai-code-review:
  stage: review
  image: python:3.12-slim
  variables:
    AI_API_KEY: $GEMINI_API_KEY
  before_script:
    # Install from GitLab repository (not published on PyPI yet)
    - pip install git+https://gitlab.com/juanjeojeda/ai-code-review.git
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

**Note:** The package is not yet published on PyPI, so you must install from the GitLab repository.

## ⚙️ Advanced Configuration

### GitLab CI/CD Variables

Set these in **Settings → CI/CD → Variables**:

#### Required Variables

```bash
# GitLab Access (set as Protected + Masked in project variables)
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx

# AI Provider (set as Protected + Masked in project variables)
GEMINI_API_KEY=your_google_gemini_api_key_here   # For Gemini
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here    # For Anthropic
```

**Note:** `GITLAB_TOKEN` is automatically available in CI/CD jobs when set as project variable. Only `AI_API_KEY` needs explicit assignment in job variables.

#### Optional Configuration Variables

```bash
# AI Configuration
AI_PROVIDER=gemini              # gemini, anthropic (cloud providers only for CI/CD - no local models)
AI_MODEL=gemini-2.5-pro         # Model name (gemini-2.5-pro, claude-sonnet-4-20250514)
TEMPERATURE=0.1                 # Response randomness (0.1 default)
MAX_TOKENS=8000                 # Max response tokens (8000 default)

# Processing Configuration
MAX_CHARS=100000               # Max diff characters (100K default)
MAX_FILES=100                  # Max files to process (100 default)
BIG_DIFFS=false                # Force 24K context (false default)
LANGUAGE_HINT=python           # Language hint for better analysis

# File Filtering
EXCLUDE_PATTERNS="*.lock,*.min.js,node_modules/**,dist/**"

# Logging
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

#### SSL Configuration for Internal GitLab Instances

For internal GitLab instances using self-signed certificates or custom CA certificates:

```bash
# SSL Configuration
SSL_VERIFY=true                # Enable SSL verification (recommended)
SSL_CERT_PATH=/path/to/company-ca.crt  # Path to your company's CA certificate

# Alternative for development/testing (NOT recommended for production)
SSL_VERIFY=false               # Disable SSL verification completely
```

##### Setting up SSL Certificates in CI/CD

1. **Upload your company's CA certificate** to your project:
   - **Settings** → **CI/CD** → **Variables**
   - Create a **File** variable named `COMPANY_CA_CERT`
   - Upload your `.crt` or `.pem` certificate file

2. **Configure the job to use the certificate:**

```yaml
ai-code-review:
  stage: review
  image: registry.gitlab.com/juanjeojeda/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    # SSL configuration for internal GitLab
    SSL_VERIFY: "true"
    SSL_CERT_PATH: $COMPANY_CA_CERT  # References the uploaded certificate file
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

##### Quick setup for development environments

```yaml
ai-code-review:
  stage: review
  image: registry.gitlab.com/juanjeojeda/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    # CAUTION: Only for development - disables SSL verification
    SSL_VERIFY: "false"
  script:
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Complete CI/CD Example

```yaml
stages:
  - test
  - review

# Your existing tests
test:
  stage: test
  script:
    - echo "Run your tests here"

# AI Code Review
ai-code-review:
  stage: review
  image: registry.gitlab.com/juanjeojeda/ai-code-review:latest
  variables:
    AI_API_KEY: $GEMINI_API_KEY
    LANGUAGE_HINT: python
    LOG_LEVEL: INFO
    # Exclude test files and docs from review
    EXCLUDE_PATTERNS: "**/*test*,docs/**,*.lock"
  script:
    # Optional: Health check first
    - ai-code-review --health-check
    # Generate and post review
    - ai-code-review --post
  allow_failure: true
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

## 💻 Local Usage

Use AI Code Review locally to analyze GitLab MRs.

### Prerequisites

```bash
# Install locally from GitLab repository (not published on PyPI yet)
pip install git+https://gitlab.com/juanjeojeda/ai-code-review.git

# Required: GitLab Personal Access Token
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx

# Optional: AI provider (Gemini/Anthropic for production, Ollama for local)
export AI_API_KEY=your_gemini_api_key     # For Gemini
export AI_API_KEY=your_anthropic_api_key  # For Anthropic
# OR use Ollama (no API key needed)
```

### Local Usage Examples

#### 1. Review and Display Only

Analyze an MR and see the review output:

```bash
# Using Gemini (production quality)
AI_API_KEY=your_key ai-code-review group/project 123

# Using Anthropic Claude (production quality)
AI_API_KEY=your_key ai-code-review group/project 123 --provider anthropic

# Using Ollama (local, free)
ai-code-review group/project 123 --provider ollama

# With custom settings
ai-code-review group/project 123 \
  --language-hint python \
  --exclude-files "**/*test*" \
  --big-diffs
```

#### 2. Review and Post to GitLab

Generate review and post it as MR comment:

```bash
# Post review to GitLab MR
AI_API_KEY=your_key ai-code-review group/project 123 --post

# With health check first (recommended)
AI_API_KEY=your_key ai-code-review --health-check && \
AI_API_KEY=your_key ai-code-review group/project 123 --post
```

#### 3. Custom GitLab Instance

For private or internal GitLab instances:

```bash
# Basic custom GitLab URL
GITLAB_TOKEN=your_token \
AI_API_KEY=your_key \
ai-code-review --gitlab-url https://gitlab.company.com \
  --project-id "internal/project" --mr-iid 456 --post
```

**For Internal GitLab with SSL Certificates:**

```bash
# Option 1: Using custom CA certificate file
GITLAB_TOKEN=your_token \
AI_API_KEY=your_key \
SSL_VERIFY=true \
SSL_CERT_PATH=/path/to/company-ca.crt \
ai-code-review --gitlab-url https://gitlab.company.com \
  internal/project 456 --post

# Option 2: Create .env file for repeated use
cat > .env << 'EOF'
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
GITLAB_URL=https://gitlab.company.com
AI_API_KEY=your_gemini_key
SSL_VERIFY=true
SSL_CERT_PATH=/path/to/company-ca.crt
EOF

# Then simply run:
ai-code-review internal/project 456 --post
```

**For Development/Testing (Disable SSL verification):**

⚠️ **CAUTION**: Only for development environments where security is not critical.

```bash
# Temporarily disable SSL verification
GITLAB_TOKEN=your_token \
AI_API_KEY=your_key \
SSL_VERIFY=false \
ai-code-review --gitlab-url https://gitlab.company.com \
  internal/project 456 --post

# Or with .env file
cat > .env << 'EOF'
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
GITLAB_URL=https://gitlab.company.com
AI_API_KEY=your_gemini_key
SSL_VERIFY=false
EOF

ai-code-review internal/project 456 --post
```

### Local Development Workflow

```bash
# 1. Set up environment
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
export AI_API_KEY=your_gemini_key

# 2. Test with dry-run (no API costs)
ai-code-review group/project 123 --dry-run

# 3. Generate review locally
ai-code-review group/project 123

# 4. If satisfied, post to GitLab
ai-code-review group/project 123 --post
```

## 🔧 Troubleshooting

### Common Issues

#### "GitLab token not configured"

```bash
# Solution: Set your GitLab token
export GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
```

#### "AI provider not available"

```bash
# Check connectivity
ai-code-review --health-check

# For Ollama: Make sure server is running
ollama serve
ollama pull qwen2.5-coder:7b
```

#### "MR not found"

```bash
# Verify project path and MR number
ai-code-review --gitlab-url https://gitlab.com group/project 123
```

#### SSL Certificate Errors

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED` or `certificate verify failed: self-signed certificate`

This occurs when connecting to internal GitLab instances with custom or self-signed certificates.

##### Solutions

1. **Use your company's CA certificate (recommended):**

    ```bash
    # Download your company's certificate first
    curl -k https://gitlab.company.com > company-ca.crt

    # Then use it
    SSL_VERIFY=true SSL_CERT_PATH=./company-ca.crt \
    ai-code-review --gitlab-url https://gitlab.company.com internal/project 456
    ```

1. **Temporarily disable SSL verification (development only):**

    ```bash
    # ⚠️ CAUTION: Only for development/testing
    SSL_VERIFY=false \
    ai-code-review --gitlab-url https://gitlab.company.com internal/project 456
    ```

1. **For CI/CD pipelines:**

    ```yaml
    # Add to your .gitlab-ci.yml
    ai-code-review:
    variables:
        SSL_VERIFY: "true"
        SSL_CERT_PATH: $COMPANY_CA_CERT  # Upload as File variable in CI/CD settings
    # ... rest of job configuration
    ```

##### Common certificate issues

- **Wrong certificate path**: Check the file exists and is readable
- **Certificate format**: Use `.crt` or `.pem` format
- **Permission issues**: Ensure the certificate file is readable by the process
- **Expired certificates**: Check certificate validity with `openssl x509 -in cert.crt -text -noout`

### Debug Mode

Enable detailed logging:

```bash
# Local debugging
LOG_LEVEL=DEBUG ai-code-review group/project 123

# CI/CD debugging (add to variables)
LOG_LEVEL: DEBUG
```

## 📚 More Information

- **Project Repository**: <https://gitlab.com/juanjeojeda/ai-code-review>
- **Issues & Support**: <https://gitlab.com/juanjeojeda/ai-code-review/-/issues>
- **Complete Documentation**: See `README.md` and `SPECS.md` in the repository
