.DEFAULT_GOAL := build

.PHONY: build
build: clean build/arn_patterns.yaml build/arn_patterns.py

build/arn_patterns.yaml:
	uv run codegen.py

build/arn_patterns.py: build/arn_patterns.yaml
	uv run codegen_python.py

.PHONY: clean
clean:
	rm -rf build/
