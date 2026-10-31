# Development setup

1. Install Python 3.12+ and PostgreSQL 16+.
2. Create and activate a virtual environment.
3. Run `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and set a strong local SECRET_KEY and DATABASE_URL.
5. Run `python manage.py makemigrations` and `python manage.py migrate`.
6. Create a local administrator with `python manage.py createsuperuser`.
7. Run tests with `pytest` and start the API with `python manage.py runserver`.

SQLite is provided only as a developer convenience. Production must use PostgreSQL, managed secrets, HTTPS and verified backups. Do not put real student or payroll information into a local test environment.
