# vim: noexpandtab, tabstop=4
#
# Install the systematic scrips and python modules
#

ifndef PREFIX
	PREFIX:=/usr/local
endif
PACKAGE= $(shell basename ${PWD})
VERSION= $(shell awk -F\' '/^VERSION/ {print $$2}' setup.py)

clean:
	@echo "Cleanup python build directories"
	rm -rf build dist *.egg-info */*.egg-info *.pyc */*.pyc */*/*.pyc

package: clean
	mkdir -p ../packages/$(PACKAGE) 
	tar -zcf ../packages/$(PACKAGE)/$(PACKAGE)-$(VERSION).tar.gz --exclude=.git --exclude=.gitignore --exclude=*.swp --exclude=*.pyc .  

register:
	python setup.py register

modules:
	python setup.py build

install_modules: modules
	@echo "Installing python modules"
	@python setup.py install

install: install_modules 
	@echo "Installing scripts to $(PREFIX)/bin/"
	@install -m 0755 -d $(PREFIX)/bin
	@for f in bin/*; do \
		echo " $(PREFIX)/$$f";install -m 755 $$f $(PREFIX)/bin/; \
	done;

