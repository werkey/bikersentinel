# Contributing to BikerSentinel

Thank you for your interest in contributing to BikerSentinel! 🏍️

## Getting Started

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/werkey/bikersentinel.git
   cd bikersentinel
   ```

2. **Create a Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests to verify setup**
   ```bash
   pytest tests/ -v
   ```

## Areas for Contribution

### Phase 2 Features (Roadmap)
- [ ] **24h Precipitation History** : Track rain patterns over time
- [ ] **Destination Weather Comparison** : Compare current vs destination conditions
- [ ] **Trajet/Trip Context** : Learn riding patterns and adapt calculations

### Quality Improvements
- [ ] Additional unit tests (target: 90%+ coverage)
- [ ] Integration tests with Home Assistant test framework
- [ ] Performance optimization for large datasets
- [ ] Documentation expansion (API docs, examples)

### Localization
- [ ] Additional language translations (translations/[lang].json)
- [ ] Regional weather entity name mappings
- [ ] Unit system support (imperial/metric improvements)

### Bug Fixes & Optimization
- [ ] Identify and fix edge cases in windchill calculation
- [ ] Optimize entity registry lookups
- [ ] Improve error handling and logging

## Pull Request Process

### Before You Start
1. **Create an issue** first to discuss your changes (optional but recommended)
2. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Making Changes
1. **Follow the code style** (existing patterns in `sensor.py` and `config_flow.py`)
2. **Add or update tests** for new features
3. **Update documentation** if behavior changes
4. **Use descriptive commit messages**:
   ```
   feat: add 24h precipitation history
   fix: correct windchill formula edge case
   docs: update configuration guide
   ```

### Testing & Validation
1. **Run all tests locally**
   ```bash
   pytest tests/ -v
   ```

2. **Verify test coverage**
   ```bash
   pytest tests/ --cov=bikersentinel --cov-report=html
   ```

3. **Check for Python style issues**
   ```bash
   pip install pylint
   pylint bikersentinel/
   ```

### Submitting Your PR
1. **Push to your fork**
2. **Create a Pull Request** with:
   - Clear title describing the change
   - Description of what changed and why
   - Reference to related issue (if applicable)
   - Any breaking changes clearly noted

3. **Wait for CI checks** (GitHub Actions will run tests automatically)
4. **Address any feedback** from maintainers

## Development Guidelines

### Code Style
- **Python version**: 3.11+ compatible
- **Async/await**: Use `async` functions for Home Assistant integration
- **Error handling**: Always catch exceptions and log with `_LOGGER`
- **Type hints**: Preferred but not mandatory

### Testing Requirements
- Minimum 75% code coverage
- All new features require unit tests
- Tests should be in `tests/test_algorithm.py`
- Use pytest fixtures from `tests/conftest.py`

### Documentation
- English only (except `translations/` directory)
- Clear docstrings for functions
- Comment complex algorithms (e.g., windchill formula)
- Update `VERIFICATION_FEATURES.md` for architectural changes

### Home Assistant Integration Specifics
- Preserve async patterns (`async_setup_entry`, etc.)
- Don't modify `Platform` or entity registry patterns
- Keep configuration keys in French (per i18n strategy)
- Test with actual Home Assistant instance if possible

## Questions?

- 📖 Read [VERIFICATION_FEATURES.md](VERIFICATION_FEATURES.md) for architecture details
- 🐛 Open an [issue](https://github.com/werkey/bikersentinel/issues) to discuss ideas

## Code of Conduct

- Be respectful and inclusive
- Welcome feedback and criticism constructively
- Help others learn and improve

---

**Happy coding! 🚀**
