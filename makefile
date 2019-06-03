.PHONY: README.rst test test-pyflakes test-pytest upload clean bootstrap

test: test-pyflakes test-pytest README.rst

test-pyflakes:
	.venv/bin/pyflakes graphlayer tests

test-pytest:
	sh -c '. .venv/bin/activate; pytest tests'

README.rst:
	.venv/bin/diff-doc compile README.src.rst > README.rst

test-all:
	tox

upload: test-all
	python setup.py sdist bdist_wheel upload
	make clean

register:
	python setup.py register

clean:
	rm -f MANIFEST
	rm -rf dist build

bootstrap: .venv
	.venv/bin/pip install -e .
ifneq ($(wildcard test-requirements.txt),)
	.venv/bin/pip install -r test-requirements.txt
endif
	make clean

.venv:
	python3.6 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install --upgrade setuptools
