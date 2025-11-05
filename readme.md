KJC Threads Automation - Python CLI

Build & run (Docker):
  docker compose up --build

Or run locally:
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  cp .env.example .env
  (edit .env)
  python main.py run-all

See README for more details.
