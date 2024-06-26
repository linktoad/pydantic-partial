clean:
	find . -name '*.pyc' -delete
	find . -name '.DS_Store' -delete
	find . -name 'packaged.yaml' -delete
	find . -name '__pycache__' -type d | xargs rm -fr
	find . -name '.pytest_cache' -type d | xargs rm -fr

run:
	PYTHONPATH=. PYTHONSTARTUP=${f} python
	make clean
