req:
	pip3 install -r requirements.txt

run:
	python3 manage.py runserver

celery:
	celery -A api_swipe worker --beat --scheduler django --loglevel=info

migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

fill-db:
	python3 manage.py users-init
	python3 manage.py flats-init

clear-db:
	python3 manage.py flats-delete
	python3 manage.py users-delete

startapp:
	python3 manage.py migrate --no-input
	python3 manage.py users-init
	python3 manage.py flats-init
	gunicorn api_swipe.wsgi:application --bind 0.0.0.0:8000
