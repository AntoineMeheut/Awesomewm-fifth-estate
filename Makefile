.PHONY: check test
check:
	python3 installer.py check

test: check
	python3 -m unittest discover -s tests -v
	lua tests/layout_test.lua
