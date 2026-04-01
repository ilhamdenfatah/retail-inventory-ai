.PHONY: build-data run test clean

build-data:
	python -m scripts.build_sample_tables

run:
	python -m app.main

test:
	python testing.py

clean:
	rm -rf __pycache__
	rm -rf */__pycache__