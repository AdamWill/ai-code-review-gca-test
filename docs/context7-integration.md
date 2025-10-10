# Context7 Integration Guide

## Overview

Context7 integration enhances AI code reviews by fetching official library documentation for your project's dependencies. This provides the LLM with authoritative information about APIs, best practices, and recommended usage patterns, leading to more accurate and helpful code reviews.

## Prerequisites

- Context7 API key (sign up at [https://context7.com])
- `aiohttp` Python package (usually already installed)
- Project must have identifiable dependencies (e.g., `requirements.txt`, `pyproject.toml`, `package.json`)

### Getting Context7 API Access

Context7 integration uses the Context7 REST API to fetch official library documentation. No additional software installation is required.

**Important**: You need a Context7 API key to use this feature.

#### How to Get API Access

1. **Sign up**: Visit [https://context7.com] and create an account
2. **Get API Key**: Generate your API key from the dashboard
3. **Set Environment Variable**: Add to your `.env` file:
   ```bash
   CONTEXT7_API_KEY=your_api_key_here
   ```

#### API Key Setup

The Context7 provider will automatically read your API key from:

1. **Environment variable**: `CONTEXT7_API_KEY`
2. **CLI parameter**: `--context7-api-key` (if implemented)
3. **Configuration file**: In `.ai_review/config.yml`

**Recommended**: Use environment variables for security:

```bash
# Add to your .env file
CONTEXT7_API_KEY=your_actual_api_key_here
```

## Configuration

### CLI Options

Enable Context7 integration using command-line flags:

```bash
# Enable Context7 with default settings
ai-generate-context . --enable-context7

# Specify priority libraries
ai-generate-context . --enable-context7 --context7-libraries "fastapi,pydantic,sqlalchemy"

# Customize token limit per library
ai-generate-context . --enable-context7 --context7-max-tokens 1500
```

### YAML Configuration

For persistent settings, configure Context7 in `.ai_review/config.yml`:

```yaml
context7:
  enabled: true
  max_libraries: 3
  max_tokens_per_library: 2000
  timeout_seconds: 10
  priority_libraries:
    - fastapi
    - pydantic
    - sqlalchemy
    - requests
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable Context7 integration |
| `max_libraries` | integer | `3` | Maximum number of libraries to fetch documentation for |
| `max_tokens_per_library` | integer | `2000` | Maximum tokens to fetch per library (100-10000) |
| `timeout_seconds` | integer | `10` | Timeout for Context7 API calls (1-60 seconds) |
| `priority_libraries` | list | `[]` | Specific libraries to fetch documentation for |

## How It Works

1. **Dependency Detection**: Context7 analyzes your project to identify dependencies
2. **Library Selection**: Selects important libraries based on priority list or built-in heuristics
3. **Documentation Fetching**: Retrieves official documentation for selected libraries in parallel
4. **LLM Enhancement**: Provides documentation context to the LLM for enhanced analysis

## Library Selection

### Priority Libraries

If you specify `priority_libraries`, Context7 will only fetch documentation for those libraries that are present in your project dependencies.

### Auto-Detection

If no priority libraries are specified, Context7 uses built-in heuristics to identify important libraries:

- **Web Frameworks**: fastapi, django, flask, starlette
- **Data & ORM**: sqlalchemy, pydantic, pandas, numpy
- **HTTP Clients**: requests, aiohttp, httpx
- **Testing**: pytest, unittest
- **Cloud & Infrastructure**: boto3, kubernetes, docker
- **ML & AI**: tensorflow, pytorch, scikit-learn, langchain

### Library Limit Configuration

The `max_libraries` setting controls how many libraries to fetch documentation for, balancing thoroughness with performance:

#### Configuration Methods

**1. YAML Configuration File** (`.ai_review/config.yml`):
```yaml
context7:
  enabled: true
  max_libraries: 5  # Fetch up to 5 libraries
```

**2. Environment Variable**:
```bash
# Set for current session
export MAX_LIBRARIES=5

# Or inline with command
MAX_LIBRARIES=5 ai-code-review generate-context
```

**3. Priority Order**: Environment variables override YAML configuration

#### Recommended Values

| Project Type | Recommended `max_libraries` | Rationale |
|--------------|----------------------------|-----------|
| **Small/Personal** | `2-3` | Fast processing, focus on core libraries |
| **Medium/Team** | `3-5` | Balanced coverage and performance |
| **Large/Enterprise** | `5-7` | Comprehensive documentation, can handle longer processing |
| **Performance Critical** | `1-2` | Minimal API calls, fastest processing |
| **Comprehensive Analysis** | `7-10` | Maximum coverage, slower but thorough |

#### Performance Considerations

- **API Calls**: Each library requires 1-2 Context7 API calls
- **Processing Time**: ~1-3 seconds per library
- **Token Usage**: Each library consumes up to `max_tokens_per_library` tokens
- **Cost**: More libraries = more API usage = higher costs

#### Examples by Project Type

```yaml
# Fast API web service
context7:
  max_libraries: 4
  priority_libraries: [fastapi, pydantic, sqlalchemy, uvicorn]

# Data science project
context7:
  max_libraries: 5
  priority_libraries: [pandas, numpy, scikit-learn, matplotlib, jupyter]

# Performance-focused (CI/CD)
context7:
  max_libraries: 2
  priority_libraries: [fastapi, pydantic]

# Comprehensive analysis
context7:
  max_libraries: 8
  priority_libraries: []  # Auto-detect all important libraries
```

## Example Configurations

### Web API Project

```yaml
context7:
  enabled: true
  priority_libraries:
    - fastapi
    - pydantic
    - sqlalchemy
    - uvicorn
    - requests
```

### Data Science Project

```yaml
context7:
  enabled: true
  priority_libraries:
    - pandas
    - numpy
    - scikit-learn
    - matplotlib
    - jupyter
```

### Django Project

```yaml
context7:
  enabled: true
  priority_libraries:
    - django
    - djangorestframework
    - celery
    - redis
    - psycopg2
```

## System Performance & Optimization

- **Parallel Fetching**: Documentation is fetched in parallel for better performance
- **Session Caching**: Results are cached during the same generation session
- **Library Limit**: Maximum of 5 libraries to avoid excessive API calls
- **Timeout Protection**: Configurable timeouts prevent hanging requests

## Troubleshooting

### Context7 API Issues

If you see warnings like:
```
WARNING: Context7 API key not available library=fastapi
INFO: Context7 section skipped - no documentation available
```

This indicates issues with Context7 API access:

#### Cause 1: Missing API Key (Most Common)

The warning `Context7 API key not available` means no API key was found. This happens when:

- `CONTEXT7_API_KEY` environment variable is not set
- API key is empty or invalid
- `.env` file is not loaded properly

**Solution**: Set your API key in the environment:
```bash
export CONTEXT7_API_KEY=your_api_key_here
# or add to .env file
echo "CONTEXT7_API_KEY=your_api_key_here" >> .env
```

#### Cause 2: API Access Issues

If you have an API key but still see errors, check:

1. **API Key Validity**: Ensure your key is active and not expired
2. **Network Connectivity**: Check internet access to context7.com
3. **Rate Limits**: You may have exceeded API rate limits
4. **Account Status**: Verify your Context7 account is in good standing

#### Cause 3: Missing Dependencies

If you see `aiohttp not available`, install it:
```bash
pip install aiohttp
# or
uv add aiohttp
```

#### Expected Behavior

If Context7 API is not available, the integration gracefully degrades:

- ✅ Context generation continues normally
- ✅ All other sections work as expected
- ⚠️ Warning messages appear (this is informational, not an error)
- ❌ No Context7 documentation section is generated

**This is the intended behavior** - Context7 is optional and won't break your workflow.

### Slow Performance

If Context7 integration is slow:

1. Reduce `max_tokens_per_library` (e.g., to 1000)
2. Decrease `timeout_seconds` (e.g., to 5)
3. Specify fewer `priority_libraries`
4. Check Context7 MCP server performance

### No Documentation Found

If no documentation is fetched:

1. Verify your project has recognizable dependencies
2. Check that priority libraries are correctly spelled
3. Ensure Context7 MCP server has access to the requested libraries
4. Try with well-known libraries (e.g., fastapi, requests)

## Integration with Code Reviews

Context7 documentation enhances code reviews by providing:

- **API Usage Patterns**: Correct ways to use library APIs
- **Best Practices**: Recommended patterns and configurations
- **Common Pitfalls**: Issues to avoid based on official documentation
- **Integration Guidelines**: How libraries should work together
- **Security Considerations**: Security best practices from documentation

## Limitations

- Requires Context7 MCP server to be available
- Limited to libraries supported by Context7
- Documentation quality depends on Context7's library coverage
- Additional API calls may increase generation time
- Token limits may restrict documentation completeness

## See Also

- [Context Generator Guide](context-generator.md)
- [Configuration Reference](../README.md#configuration)
- [Troubleshooting Guide](user-guide.md#troubleshooting)
