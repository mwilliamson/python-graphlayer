.PHONY: README.rst test test-pyflakes test-pytest clean

test: tox

test-pyflakes:
	.venv/bin/pyflakes graphlayer tests

test-pytest:
	sh -c '. .venv/bin/activate; pytest tests'

README.rst:
	.venv/bin/diff-doc compile README.src.rst > README.rst

clean: rm-pyenv
	rm -rf .tox *.egg-info

.venv:
	python3.8 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install poetry
	poetry install