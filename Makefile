.PHONY: install lint fmt test demo clean

install:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src tests

fmt:
	ruff format src tests

test:
	pytest --cov=llm_bench --cov-report=term-missing

demo:
	python scripts/regenerate_demo.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage coverage.xml htmlcov dist build
