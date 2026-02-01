# uv Package Manager Migration Guide

This document describes the migration from pip/poetry to uv package manager.

## What Changed

### Build System

- **Before**: `setuptools` build backend
- **After**: `hatchling` build backend (uv-optimized)

### Python Version

- **Before**: `>=3.11` (supports 3.11, 3.12, 3.13)
- **After**: `>=3.13` (Python 3.13 only)

### Package Management

- **Before**: `pip install -e .`
- **After**: `uv pip install -e .`

### Code Formatting

- **Before**: `black` for formatting
- **After**: `ruff format` (built into ruff)

## New Files

### `.python-version`

Specifies Python version for uv:

```
3.13
```

### `.uvrc`

uv configuration file:

```toml
dev-dependencies = true
python-version = "3.13"
cache-dir = ".uv-cache"
workspace = true
```

### `scripts/install.sh`

Automated installation script using uv.

### `docs/DEVELOPMENT.md`

Development setup guide with uv commands.

## Updated Files

### `pyproject.toml`

- Changed build system to `hatchling`
- Added `[tool.uv]` configuration section
- Consolidated ruff configuration (removed duplicate sections)
- Removed `black` configuration (use ruff format instead)
- Updated mypy python_version to 3.13

### Dockerfiles

All Dockerfiles now use uv for faster dependency installation:

- `Dockerfile`
- `Dockerfile.mcp`
- `Dockerfile.communication`

### `scripts/dev.sh`

Updated `format_code()` and `type_check()` functions to use `uv run`.

### `README.md`

Updated installation and code quality instructions.

## Migration Steps for Existing Projects

If you have an existing installation:

1. **Remove old virtual environment**:
   ```bash
   rm -rf .venv
   ```

2. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Run installation script**:
   ```bash
   ./scripts/install.sh
   ```

4. **Verify installation**:
   ```bash
   source .venv/bin/activate
   python -c "import mcp_broker; print('OK')"
   ```

## Benefits of uv

- **Speed**: 10-100x faster than pip
- **Reliability**: Better dependency resolution
- **Compatibility**: Drop-in replacement for pip
- **Cache**: Smart caching for faster reinstalls

## Commands Reference

| Task | pip | uv |
|------|-----|-----|
| Install package | `pip install pkg` | `uv pip install pkg` |
| Install project | `pip install -e .` | `uv pip install -e .` |
| Install with extras | `pip install -e ".[dev]"` | `uv pip install -e ".[dev]"` |
| Create venv | `python -m venv .venv` | `uv venv` |
| Run in venv | `source .venv/bin/activate; cmd` | `uv run cmd` |

## Troubleshooting

### uv command not found

Add to PATH:
```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

### Import errors after migration

Reinstall in editable mode:
```bash
uv pip install -e .
```

### Docker build fails

Make sure you're using the updated Dockerfiles that include uv installation.

## Further Reading

- [uv documentation](https://github.com/astral-sh/uv)
- [Why uv?](https://astral.sh/blog/uv)
- [Ruff Formatter](https://docs.astral.sh/ruff/formatter/)
