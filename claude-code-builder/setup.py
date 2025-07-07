"""Setup script for Claude Code Builder."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="claude-code-builder",
    version="3.0.0",
    author="Claude Code Builder Team",
    author_email="team@claudecodebuilder.ai",
    description="AI-Driven Autonomous Project Builder using Claude Code SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/claude-code-builder/claude-code-builder",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "anthropic>=0.31.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pydantic>=2.0.0",
        "aiohttp>=3.9.0",
        "jinja2>=3.1.0",
        "pyyaml>=6.0",
        "jsonschema>=4.0.0",
        "python-dotenv>=1.0.0",
        "tenacity>=8.2.0",
        "psutil>=5.9.0",
        "watchdog>=3.0.0",
        "pytest>=7.4.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.1.0",
        "black>=23.0.0",
        "mypy>=1.5.0",
        "ruff>=0.1.0",
        "httpx>=0.25.0",
        "anyio>=4.0.0"
    ],
    extras_require={
        "dev": [
            "pytest-mock>=3.11.0",
            "pytest-timeout>=2.1.0",
            "pytest-xdist>=3.3.0",
            "coverage[toml]>=7.3.0",
            "pre-commit>=3.3.0",
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-click>=5.0.0",
            "myst-parser>=2.0.0",
        ],
        "research": [
            "perplexity-client>=0.1.0",
            "openai>=1.0.0",
            "langchain>=0.1.0",
            "chromadb>=0.4.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "claude-code-builder=claude_code_builder.cli:main",
            "ccb=claude_code_builder.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="claude ai code-generation project-builder automation development-tools",
    project_urls={
        "Documentation": "https://claude-code-builder.readthedocs.io",
        "Source": "https://github.com/claude-code-builder/claude-code-builder",
        "Issues": "https://github.com/claude-code-builder/claude-code-builder/issues",
    },
)