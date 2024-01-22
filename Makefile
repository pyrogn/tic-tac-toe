init:
	python -m pip install maturin
	maturin develop --release

test:
	pytest
