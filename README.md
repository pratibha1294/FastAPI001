# FastAPI001

A FastAPI service backed by MySQL, with schema managed through Alembic (pure-SQL migrations).

## Stack

- [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/)
- MySQL 8.0 (via Docker Compose)
- [SQLAlchemy](https://www.sqlalchemy.org/) (engine/connection only — no ORM models)
- [Alembic](https://alembic.sqlalchemy.org/) for migrations, written as raw SQL
- [uv](https://docs.astral.sh/uv/) for dependency management

## Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker](https://www.docker.com/) + Docker Compose (for MySQL)

## 1. Configure environment

Copy the example env file and adjust values if needed:

```bash
cp .env.example .env
```

`.env` variables:

| Variable            | Purpose                                      | Default        |
|---------------------|-----------------------------------------------|----------------|
| `MYSQL_DATABASE`    | Database name                                  | `fastapi001`   |
| `MYSQL_USER`        | App DB user                                    | `fastapi001`   |
| `MYSQL_PASSWORD`    | App DB user password                           | `changeme`     |
| `MYSQL_ROOT_PASSWORD` | MySQL root password                          | `changeme_root`|
| `MYSQL_HOST`        | DB host (from the machine running Alembic/app) | `localhost`    |
| `MYSQL_PORT`        | DB port on the host                            | `3307`         |

**Note:** MySQL is exposed on host port `3307` (mapped to the container's `3306`) to avoid clashing with any local MySQL install.

## 2. Start MySQL

```bash
docker compose up -d
```

This starts a MySQL 8.0 container (`fastapi001_mysql`) with a persistent volume, healthcheck, and credentials from `.env`.

To stop it:

```bash
docker compose down
```

To stop it and wipe the database volume:

```bash
docker compose down -v
```

## 3. Install dependencies

```bash
uv sync
```

This creates/updates `.venv` from `pyproject.toml` / `uv.lock`.

## 4. Run database migrations

Migrations live in `alembic/versions/` and are written as raw SQL via `op.execute()`.

Apply all migrations:

```bash
uv run alembic upgrade head
```

Other useful commands:

```bash
uv run alembic current          # show current DB revision
uv run alembic history          # list all revisions
uv run alembic downgrade -1     # roll back one revision
`uv run alembic revision -m "description"`   # create a new empty migration (fill in raw SQL)
```

## 5. Run the app

```bash
uv run uvicorn app:app --reload
```

The app will be available at http://127.0.0.1:8000.

- `GET /` → `{"message": "Hello, FastAPI!"}`
- `GET /health` → `{"status": "ok"}`

Interactive API docs: http://127.0.0.1:8000/docs

## Project layout

```
app.py                  # FastAPI application entrypoint
docker-compose.yml       # MySQL service definition
alembic.ini              # Alembic configuration
alembic/
  env.py                 # builds DB URL from .env, runs migrations
  versions/               # migration scripts (raw SQL)
.env.example              # template for local environment variables
```

## Troubleshooting

- **Alembic can't connect to MySQL**: confirm the container is running (`docker compose ps`) and `.env` matches the port in `docker-compose.yml` (default `3307`).
- **Port 3307 already in use**: change the host port in `docker-compose.yml` (`ports: "XXXX:3306"`) and update `MYSQL_PORT` in `.env` to match.
