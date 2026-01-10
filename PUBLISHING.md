# Publishing Guide

## Publishing to PyPI

This guide explains how to publish the Escalation Engine package to the Python Package Index (PyPI).

### Prerequisites

1. **PyPI Account**: Create an account at https://pypi.org/account/register/

2. **Install Build Tools**:
   ```bash
   pip install build twine
   ```

3. **API Token**: Create an API token at https://pypi.org/manage/account/token/

### Step 1: Update Version

Update the version in `pyproject.toml`:
```toml
[project]
name = "escalation-engine"
version = "1.0.0"  # Update this
```

### Step 2: Build the Package

```bash
cd /path/to/escalation-engine
python -m build
```

This creates:
- `dist/escalation_engine-1.0.0.tar.gz` (source distribution)
- `dist/escalation_engine-1.0.0-py3-none-any.whl` (wheel)

### Step 3: Check the Package

```bash
twine check dist/*
```

### Step 4: Test on TestPyPI (Optional)

1. Upload to TestPyPI:
   ```bash
   twine upload --repository testpypi dist/*
   ```

2. Install from TestPyPI:
   ```bash
   pip install --index-url https://test.pypi.org/simple/ escalation-engine
   ```

### Step 5: Publish to PyPI

```bash
twine upload dist/*
```

You'll be prompted for your PyPI username and password (use your API token as the password).

### Step 6: Verify

1. Visit https://pypi.org/project/escalation-engine/
2. Test installation:
   ```bash
   pip install escalation-engine
   ```

## Publishing to npm (TypeScript Version)

If you create a TypeScript/JavaScript version:

### Prerequisites

```bash
npm install -g typescript tsdx
```

### Build

```bash
npm run build
```

### Publish

```bash
npm publish
```

## Versioning

Follow Semantic Versioning:
- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

Example: `1.0.0` -> `1.0.1` (bug fix) -> `1.1.0` (new feature) -> `2.0.0` (breaking change)

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md
- [ ] Run all tests: `pytest`
- [ ] Build package: `python -m build`
- [ ] Check package: `twine check dist/*`
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Verify installation from PyPI
- [ ] Tag release in git: `git tag v1.0.0`
- [ ] Push tag: `git push --tags`
