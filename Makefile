.PHONY: run install clean test lint

install:
	pip install -r requirements.txt

run:
	python app.py

test:
	python -m pytest test_routes.py -v

lint:
	flake8 app.py models.py config.py --max-line-length=120

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f *.db

freeze:
	pip freeze > requirements.txt
