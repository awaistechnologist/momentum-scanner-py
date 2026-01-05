# Contributing to Momentum Stock Scanner

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/awaistechnologist/momentum-scanner-py.git`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit and push
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/awaistechnologist/kairos.git
cd share-tracker

# Install dependencies
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt  # If you create one
```

## Security Guidelines

### 🔐 NEVER Commit Sensitive Data

Before committing, always verify:

```bash
# Check what you're committing
git status
git diff --cached

# Ensure these files are NOT staged:
# - .env
# - config.json
# - Any file with API keys
```

### Install Pre-commit Hook (Recommended)

```bash
# Link the pre-commit hook
ln -s ../../scripts/pre-commit-check.sh .git/hooks/pre-commit

# Make it executable (should already be)
chmod +x .git/hooks/pre-commit
```

This hook will:
- Prevent committing `.env` and `config.json`
- Warn if potential API keys are detected
- Save you from accidental leaks

### Use Example Files

- Use `.env.example` as a template (contains no real keys)
- Use `scanner/config/config.example.json` for config templates
- Never put real API keys in example files

## Code Style

### Python
- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and under 50 lines when possible

### Formatting
```bash
# Use black for formatting (if installed)
black scanner/

# Use isort for imports (if installed)
isort scanner/
```

## Testing

Before submitting a PR:

```bash
# Run the test installation script
python scripts/test_installation.py

# Test the CLI
python -m scanner.modes.cli --symbols AAPL

# Test the UI (if you modified it)
python scripts/run_ui.py
```

## Commit Messages

Use clear, descriptive commit messages:

```bash
# Good
git commit -m "Add batch API support for Alpha Vantage provider"
git commit -m "Fix RSI calculation for edge cases"

# Bad
git commit -m "fix bug"
git commit -m "updates"
```

### Commit Message Format

```
<type>: <short description>

<longer description if needed>

<issue references if applicable>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

## Pull Request Process

1. **Update documentation** if you've changed functionality
2. **Add tests** if you've added features
3. **Ensure all tests pass**
4. **Update CHANGELOG.md** (if exists)
5. **Link related issues** in your PR description

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No sensitive data committed
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

## Areas for Contribution

### High Priority
- Additional data providers (Yahoo Finance, IEX Cloud, etc.)
- More technical indicators (Bollinger Bands, Stochastic, etc.)
- Backtesting functionality
- Performance optimizations

### Medium Priority
- Additional export formats (Excel, PDF reports)
- More chart types in UI
- Email notifications
- Docker support

### Documentation
- More examples in docs/
- Video tutorials
- API documentation
- Translation to other languages

## Questions?

- Open an issue with the "question" label
- Check existing issues and discussions
- Read the documentation in `docs/`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism
- Focus on what's best for the project
- Show empathy towards others

### Unacceptable Behavior

- Harassment or discriminatory language
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

Thank you for contributing! 🚀
