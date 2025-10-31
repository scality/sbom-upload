# Contributing to SBOM Upload

Welcome! 🎉 We're excited that you want to contribute to the SBOM Upload project. This guide will help you get started quickly and run tests efficiently.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git

### Setup Development Environment

1. **Clone the repository**

   ```bash
   git clone https://github.com/scality/sbom-upload.git
   cd sbom-upload
   ```

2. **Create and activate virtual environment or use Dev Container**

   If you prefer using a virtual environment, you can create one with:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

   Alternatively, you can use the provided Dev Container for a consistent development environment.

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install pre-commit hooks** (optional but recommended)

   ```bash
   pre-commit install
   ```

## 🧪 Rapid Testing Guide

### Quick Test Commands

| Test Type | Command | Duration | Description |
|-----------|---------|----------|-------------|
| **Unit Tests** | `python tests/test_version.py` | ~2s | Test version comparison functions |
| **Integration** | `bash tests/test-workflow.sh` | ~10s | Full workflow simulation |
| **Dry Run** | `INPUT_DRY_RUN=true python src/main.py` | ~5s | Safe execution test |
| **Syntax Check** | `python -m py_compile src/**/*.py` | ~1s | Python syntax validation |

### 🏃‍♂️ 30-Second Test Suite

Run this for quick validation before committing:

```bash
# Quick validation pipeline
echo "🧪 Running 30-second test suite..."

# 1. Syntax check (1-2s)
echo "1/4 Checking syntax..."
python -m py_compile src/main.py src/cli/*.py src/domain/*.py

# 2. Version tests (2-3s)
echo "2/4 Testing version functions..."
python tests/test_version.py

# 3. Import tests (2-3s)
echo "3/4 Testing imports..."
python -c "from src.main import *; print('✅ Main imports OK')"

# 4. Dry run test (3-5s)
echo "4/4 Testing dry run..."
cd src && INPUT_DRY_RUN=true python main.py --help

echo "✅ All quick tests passed!"
```

### 📊 Test Levels

#### Level 1: Lightning Tests ⚡ (< 5 seconds)

```bash
# Syntax and basic functionality
python -m py_compile src/**/*.py
python tests/test_version.py
```

#### Level 2: Standard Tests 🔧 (< 30 seconds)

```bash
# Include integration and workflow tests
bash tests/test-workflow.sh
INPUT_DRY_RUN=true python src/main.py
```

#### Level 3: Full Test Suite 🚀 (< 2 minutes)

```bash
# Complete testing including edge cases
export INPUT_URL="http://localhost:8081"
export INPUT_API_KEY="test_key"
bash tests/test-workflow.sh
```

## 🔧 Development Workflow

### Before Making Changes

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Run baseline tests**

   ```bash
   python tests/test_version.py  # Should pass
   ```

### During Development

1. **Test frequently** - Run Level 1 tests after each significant change
2. **Use dry run mode** - Always test with `INPUT_DRY_RUN=true` first
3. **Check imports** - Ensure new modules import correctly

### Before Committing

1. **Run the 30-second test suite** (see above)
2. **Check code style** (if pre-commit is installed, it runs automatically)
3. **Test edge cases** with different SBOM files in `tests/single_sbom/` and `tests/multiple_sbom/`

## 🐛 Debugging & Troubleshooting

### Common Issues

| Issue | Quick Fix | Test Command |
|-------|-----------|-------------|
| Import errors | Check PYTHONPATH | `python -c "import sys; print(sys.path)"` |
| Connection issues | Use dry run mode | `INPUT_DRY_RUN=true python src/main.py` |
| Version conflicts | Check requirements | `pip list \| grep -E "(requests\|click\|pydantic)"` |

## 📁 Test Data

The `tests/` directory contains:

- `single_sbom/` - Individual SBOM files for testing
- `multiple_sbom/` - Multiple SBOM files for batch testing
- `api/spec.json` - API specification for validation
- `docker/` - Docker compose for local testing environment

## 🔄 CI/CD Pipeline

Our GitHub Actions automatically run:

1. **Syntax validation** - Python compilation check
2. **Unit tests** - Core functionality testing
3. **Integration tests** - Full workflow simulation
4. **Security scans** - Dependency vulnerability checks

## 📝 Code Style

- Follow PEP 8 conventions
- Use type hints where possible
- Add docstrings for public functions
- Keep functions focused and testable

## 🌟 GitHub Codespaces

This project is configured for GitHub Codespaces. Click to open:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/scality/sbom)
