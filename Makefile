#
# Install the scrips, configs and python modules
#

all:
	flake8 | sort

clean:
	@rm -rf build dist .DS_Store .cache .eggs
	@find . -name '*.egg-info' -print0|xargs -0 rm -rf
	@find . -name '*.pyc' -print0|xargs -0 rm -rf

build:
	python setup.py build

ifdef PREFIX
install: build
	python setup.py --no-user-cfg install --prefix=${PREFIX}
else
install: build
	python setup.py install
endif

upload: clean
	python setup.py sdist bdist_wheel
	twine upload dist/*

test:
	python setup.py test

.PHONY: all test
