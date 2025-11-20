.PHONY: test run install-hooks

# Run tests
test:
	pytest -q

# Run Streamlit app
run:
	streamlit run app.py

# Install pre-commit hooks
install-hooks:
	pre-commit install

# Format code with black
format:
	black src/ tests/ app.py

# Lint code with ruff
lint:
	ruff check src/ tests/ app.py

# Format and lint
fix: format lint 