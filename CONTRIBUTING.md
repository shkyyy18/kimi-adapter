# Contributing

Thanks for your interest in Kimi Adapter!

## Development Setup

```bash
git clone https://github.com/njshk/kimi-adapter.git
cd kimi-adapter
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

## Linting and Formatting

```bash
ruff check .
black --check .
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Add tests for new behavior
4. Ensure CI passes
5. Open a pull request with a clear description

## Reporting Issues

Please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Any relevant logs
