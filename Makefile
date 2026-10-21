install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
up:
	docker compose up -d --wait
demo: up
	.venv/bin/python pipeline.py
test: up
	.venv/bin/python -m unittest -v
down:
	docker compose down -v
