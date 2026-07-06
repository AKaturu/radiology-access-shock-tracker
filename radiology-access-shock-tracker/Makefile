.PHONY: install demo test lint dashboard clean

install:
	python -m pip install -e ".[dev]"

demo:
	radshock demo --output-dir outputs/demo

test:
	pytest

lint:
	ruff check .

dashboard:
	streamlit run src/radshock/app.py

clean:
	rm -rf outputs .pytest_cache .ruff_cache .mypy_cache
