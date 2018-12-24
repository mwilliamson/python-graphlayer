.PHONY: test upload clean bootstrap

test:
	.venv/bin/pyflakes graphlayer tests
	sh -c '. .venv/bin/activate; pytest tests'

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
	python3.5 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install --upgrade setuptools
