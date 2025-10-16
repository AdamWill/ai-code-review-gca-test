"""Constants for context generator."""

from __future__ import annotations

# Important file extensions for code and configuration
IMPORTANT_EXTENSIONS = {
    ".py",  # Python
    ".js",  # JavaScript
    ".ts",  # TypeScript
    ".jsx",  # React JSX
    ".tsx",  # React TypeScript
    ".go",  # Go
    ".rs",  # Rust
    ".java",  # Java
    ".c",  # C
    ".cpp",  # C++
    ".cc",  # C++
    ".cxx",  # C++
    ".h",  # C/C++ Header
    ".hpp",  # C++ Header
    ".rb",  # Ruby
    ".php",  # PHP
    ".sh",  # Shell script
    ".bash",  # Bash script
    ".zsh",  # Zsh script
    ".fish",  # Fish script
    ".ps1",  # PowerShell
    ".bat",  # Batch
    ".cmd",  # Command
    ".fmf",  # FMF (testing)
    ".yml",  # YAML
    ".yaml",  # YAML
    ".json",  # JSON
    ".toml",  # TOML
    ".xml",  # XML
    ".ini",  # INI
    ".cfg",  # Config
    ".conf",  # Config
    ".md",  # Markdown
    ".rst",  # reStructuredText
    ".txt",  # Text
    ".sql",  # SQL
    ".r",  # R
    ".R",  # R
    ".scala",  # Scala
    ".kt",  # Kotlin
    ".swift",  # Swift
    ".dart",  # Dart
    ".lua",  # Lua
    ".pl",  # Perl
    ".pm",  # Perl Module
    ".vim",  # Vim script
    ".el",  # Emacs Lisp
}

# Important files without extensions
IMPORTANT_FILES_NO_EXT = {
    "Containerfile",
    "Dockerfile",
    "Makefile",
    "makefile",
    "GNUmakefile",
    "Jenkinsfile",
    "Vagrantfile",
    "Gemfile",
    "Rakefile",
    "Guardfile",
    "Procfile",
    "Brewfile",
    "Pipfile",
    "Justfile",
    "LICENSE",
    "LICENCE",
    "COPYING",
    "COPYRIGHT",
    "CHANGELOG",
    "CHANGES",
    "HISTORY",
    "NEWS",
    "NOTICE",
    "AUTHORS",
    "CONTRIBUTORS",
    "MAINTAINERS",
    "CODEOWNERS",
    "SECURITY",
}

# Important root files for different project types
IMPORTANT_ROOT_FILES = {
    # Python
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "conda.yml",
    "environment.yml",
    "tox.ini",
    "pytest.ini",
    "mypy.ini",
    ".python-version",
    # JavaScript/Node.js
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bower.json",
    ".nvmrc",
    ".node-version",
    "webpack.config.js",
    "vite.config.js",
    "rollup.config.js",
    "tsconfig.json",
    "jsconfig.json",
    "babel.config.js",
    ".babelrc",
    "eslint.config.js",
    ".eslintrc.js",
    ".eslintrc.json",
    "prettier.config.js",
    ".prettierrc",
    # Ruby
    "Gemfile",
    "Gemfile.lock",
    ".ruby-version",
    ".rvmrc",
    "config.ru",
    # Go
    "go.mod",
    "go.sum",
    "go.work",
    "go.work.sum",
    # Rust
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain",
    "rust-toolchain.toml",
    # Java/JVM
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "gradle.properties",
    "gradlew",
    "gradlew.bat",
    "build.xml",
    "ivy.xml",
    "project.clj",
    "deps.edn",
    "build.sbt",
    # C/C++
    "CMakeLists.txt",
    "configure.ac",
    "configure.in",
    "Makefile.am",
    "meson.build",
    "conanfile.txt",
    "conanfile.py",
    "vcpkg.json",
    # .NET
    "*.csproj",
    "*.fsproj",
    "*.vbproj",
    "*.sln",
    "Directory.Build.props",
    "Directory.Build.targets",
    "global.json",
    "nuget.config",
    # PHP
    "composer.json",
    "composer.lock",
    "artisan",
    # Docker/Containers
    "Dockerfile",
    "Containerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "docker-compose.override.yml",
    ".dockerignore",
    # CI/CD
    ".gitlab-ci.yml",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "Jenkinsfile",
    "appveyor.yml",
    "azure-pipelines.yml",
    ".circleci/config.yml",
    # Documentation
    "README.md",
    "README.rst",
    "README.txt",
    "README",
    "CONTRIBUTING.md",
    "CONTRIBUTING.rst",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    # Configuration
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".pre-commit-config.yaml",
    ".pre-commit-hooks.yaml",
    "renovate.json",
    ".renovaterc",
    "dependabot.yml",
}

# Priority files for Python projects (used in structure analysis)
PRIORITY_PYTHON_FILES = {
    "cli.py",
    "config.py",
    "main.py",
    "app.py",
    "__main__.py",
    "__init__.py",
    "settings.py",
    "models.py",
    "views.py",
    "urls.py",
    "wsgi.py",
    "asgi.py",
}

# Dependency file patterns for different languages
DEPENDENCY_FILE_PATTERNS = {
    "pyproject.toml",
    "requirements.txt",
    "setup.py",  # Python
    "package.json",
    "yarn.lock",
    "package-lock.json",  # JavaScript/Node
    "Gemfile",
    "Gemfile.lock",  # Ruby
    "go.mod",
    "go.sum",  # Go
    "Cargo.toml",
    "Cargo.lock",  # Rust
    "pom.xml",
    "build.gradle",  # Java
    "composer.json",  # PHP
}

# Framework categorization by language
PYTHON_FRAMEWORKS = {"fastapi", "flask", "django", "starlette", "tornado", "bottle"}

PYTHON_TESTING_TOOLS = {"pytest", "unittest", "nose2", "tox", "coverage"}

JAVASCRIPT_FRAMEWORKS = {"react", "vue", "angular", "express", "next", "nuxt", "svelte"}

JAVASCRIPT_TESTING_TOOLS = {"jest", "mocha", "chai", "cypress", "playwright", "vitest"}

RUBY_FRAMEWORKS = {"rails", "sinatra", "hanami", "roda", "dashing", "smashing"}

RUBY_TESTING_TOOLS = {"rspec", "minitest", "capybara", "factory_bot", "cucumber"}

GO_FRAMEWORKS = {"gin-gonic/gin", "gorilla/mux", "labstack/echo", "fiber", "chi"}

GO_TESTING_TOOLS = {"testify", "ginkgo", "gomega", "goconvey"}

RUST_FRAMEWORKS = {"actix-web", "warp", "rocket", "axum", "tide", "hyper"}

RUST_TESTING_TOOLS = {"tokio-test", "rstest", "proptest", "quickcheck"}

JAVA_FRAMEWORKS = {"spring-boot", "spring-web", "quarkus", "micronaut", "dropwizard"}

JAVA_TESTING_TOOLS = {"junit", "testng", "mockito", "assertj", "wiremock"}

# Language detection by file extension
LANGUAGE_EXTENSIONS = {
    "py": "Python",
    "js": "JavaScript/TypeScript",
    "ts": "JavaScript/TypeScript",
    "jsx": "JavaScript/TypeScript",
    "tsx": "JavaScript/TypeScript",
    "java": "Java",
    "go": "Go",
    "rs": "Rust",
    "rb": "Ruby",
    "php": "PHP",
    "c": "C",
    "cpp": "C++",
    "cc": "C++",
    "cxx": "C++",
    "h": "C/C++",
    "hpp": "C++",
}

# Entry point file patterns for different languages
ENTRY_POINT_PATTERNS = [
    # Python entry points
    "src/*/cli.py",
    "src/*/main.py",
    "**/cli.py",
    "**/main.py",
    "main.py",
    "app.py",
    "__main__.py",
    # JavaScript/TypeScript entry points
    "src/index.js",
    "src/index.ts",
    "src/main.js",
    "src/main.ts",
    "index.js",
    "index.ts",
    "server.js",
    "app.js",
    # Go entry points
    "main.go",
    "cmd/*/main.go",
    "cmd/*/*/main.go",
    # Rust entry points
    "src/main.rs",
    "src/bin/*.rs",
    # Java entry points
    "**/Main.java",
    "**/Application.java",
    "**/App.java",
    "src/main/java/**/Main.java",
    "src/main/java/**/Application.java",
    # C/C++ entry points
    "main.c",
    "main.cpp",
    "main.cc",
    "src/main.c",
    "src/main.cpp",
    # Ruby entry points
    "bin/*",
    "exe/*",
    "lib/*/cli.rb",
    "lib/*/main.rb",
    # Shell scripts
    "bin/*.sh",
    "lib/*.sh",
    "scripts/*.sh",
    "*.sh",
]

# Configuration file patterns for different languages
CONFIG_FILE_PATTERNS = [
    # Python config
    "src/*/config.py",
    "src/*/settings.py",
    "**/config.py",
    "**/settings.py",
    "config.py",
    "settings.py",
    # JavaScript/TypeScript config
    "src/config.js",
    "src/config.ts",
    "config/index.js",
    "config/index.ts",
    "config.js",
    "config.ts",
    # Go config
    "config/config.go",
    "pkg/config/*.go",
    "internal/config/*.go",
    # Rust config
    "src/config.rs",
    "src/config/mod.rs",
    # Java config
    "src/main/java/**/config/*.java",
    "src/main/java/**/Config.java",
    "src/main/resources/application.properties",
    "src/main/resources/application.yml",
    # Ruby config
    "config/*.rb",
    "lib/*/config.rb",
    # C/C++ config
    "config.h",
    "src/config.h",
    "include/config.h",
]

# Context7 library selection constants
CONTEXT7_IMPORTANT_LIBRARIES = {
    # Web frameworks
    "fastapi",
    "django",
    "flask",
    "starlette",
    "uvicorn",
    "gunicorn",
    # Data & ORM
    "sqlalchemy",
    "pydantic",
    "pandas",
    "numpy",
    "requests",
    "httpx",
    "aiohttp",
    # Testing
    "pytest",
    "unittest",
    "mock",
    # Async
    "asyncio",
    "celery",
    "redis",
    # CLI
    "click",
    "typer",
    "argparse",
    # Utilities
    "pathlib",
    "datetime",
    "json",
    "yaml",
    "toml",
    # JavaScript/TypeScript
    "react",
    "vue",
    "angular",
    "express",
    "next",
    "nuxt",
    "svelte",
    "axios",
    "lodash",
    "moment",
    "dayjs",
    # Node.js
    "node",
    "npm",
    "yarn",
    "webpack",
    "vite",
    "rollup",
    # Testing (JS)
    "jest",
    "mocha",
    "chai",
    "cypress",
    "playwright",
    # Go
    "gin",
    "echo",
    "fiber",
    "gorilla/mux",
    "gorm",
    "testify",
    # Rust
    "actix-web",
    "warp",
    "rocket",
    "axum",
    "serde",
    "tokio",
    "reqwest",
    # Java
    "spring-boot",
    "spring-web",
    "hibernate",
    "junit",
    "mockito",
    # Ruby
    "rails",
    "sinatra",
    "rspec",
    "capybara",
    # PHP
    "laravel",
    "symfony",
    "phpunit",
    # Database
    "postgresql",
    "mysql",
    "sqlite",
    "mongodb",
    "elasticsearch",
}

# Default maximum number of libraries to fetch documentation for
CONTEXT7_DEFAULT_MAX_LIBRARIES = 3

# CI/CD system Context7 library names
CI_SYSTEM_CONTEXT7_LIBRARIES = {
    "gitlab-ci": "/websites/docs_gitlab_com",
    "github-actions": "/github/docs",
}

# Context7 library ID denylist patterns (documentation sites, not actual libraries)
# CI/CD documentation should be handled exclusively by CIDocsSection when enabled
CONTEXT7_LIBRARY_DENYLIST_PATTERNS = [
    "/websites/",  # Documentation sites (e.g., docs.gitlab.com)
    "/github/docs",  # GitHub documentation site
    "/docs/",  # Generic docs sites
    "/tutorials/",  # Tutorial sites
]

# Minimum trust score for library selection
CONTEXT7_MIN_TRUST_SCORE = 5

# Official library patterns (higher priority)
CONTEXT7_OFFICIAL_LIBRARY_PATTERNS = {
    "react": ["/facebook/react", "/reactjs/"],
    "vue": ["/vuejs/"],
    "angular": ["/angular/"],
    "django": ["/django/"],
    "flask": ["/pallets/flask"],
    "fastapi": ["/tiangolo/fastapi"],
    "nextjs": ["/vercel/next"],
    "express": ["/expressjs/"],
    "typescript": ["/microsoft/typescript"],
}
