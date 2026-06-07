.PHONY: help test install clean count

help:		## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

test:		## Run the offline test suite (no deps)
	cd .. && python -m unittest discover -s hyperloglog/tests -t . -v

install:	## Editable install of the package
	pip install -e .

count:		## Estimate distinct lines: make count ARGS='access.log --exact'
	python -m hyperloglog $(ARGS)

clean:		## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf *.egg-info build dist .eggs
