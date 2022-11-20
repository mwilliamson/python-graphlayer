.PHONY: test

test: test-pyflakes test-pytest README.rst

.PHONY: test-pyflakes

test-pyflakes:
	.venv/bin/pyflakes graphlayer tests

.PHONY: test-pytest

test-pytest:
	sh -c '. .venv/bin/activate; pytest tests'

README.rst:
	.venv/bin/diff-doc compile README.src.rst > README.rst

.PHONY: test-all

test-all:
	tox

.PHONY: upload

upload: build-dist
	_virtualenv/bin/twine upload dist/*
	make clean

.PHONY: build-dist

build-dist: clean
	_virtualenv/bin/pyproject-build

.PHONY: clean

clean:
	rm -f MANIFEST
	rm -rf build dist

.PHONY: bootstrap

bootstrap: _virtualenv
	_virtualenv/bin/pip install -e .
ifneq ($(wildcard test-requirements.txt),)
	_virtualenv/bin/pip install -r test-requirements.txt
endif
	make clean

.venv:
	python3 -m venv _virtualenv
	_virtualenv/bin/pip install --upgrade pip
	_virtualenv/bin/pip install --upgrade setuptools
	_virtualenv/bin/pip install --upgrade wheel
	_virtualenv/bin/pip install --upgrade build twine
