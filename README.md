# Product Sentiment Analysis MVP

Real-time social sensing platform comparing sentiment between product launches (demo: iPhone 16 vs iPhone 17) with runtime-configurable product lists.

## Features

- FastAPI backend with endpoints for discovery, ingestion, classification, metrics, summaries, semantic search, and news seeds.
- Streamlit dashboard for configuring products, triggering ingestion, exploring analytics, and semantic search.
- Alias expansion via OpenAI for better source discovery.
- Reddit (PRAW) and YouTube Data API integrations (no scraping) with full comment ingestion.
- PostgreSQL storage with normalized schema and indices.
- NLP pipeline using OpenAI (sentiment, aspects, summaries) with VADER fallback.
- Weaviate vector database storing embeddings for semantic exploration.
- Docker Compose stack for Postgres and Weaviate; backend/UI run locally during development.
- Unit tests for utility and integration helpers.

## Quickstart

1. **Install dependencies**

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment variables**

   Copy `.env.example` to `.env` and populate the required keys:

   - `OPENAI_API_KEY`
   - `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
   - `YOUTUBE_API_KEY`
   - `WEAVIATE_ENDPOINT`, `WEAVIATE_API_KEY`
   - `DATABASE_URL` (e.g., `postgresql+psycopg2://postgres:postgres@localhost:5432/socialsense`)

3. **Start dependencies**

   ```bash
   docker-compose up -d
   ```

4. **Run migrations (initial schema)**

   ```bash
   python -m app.db.models
   ```

   The SQLAlchemy models define the schema. choco install make -y tables as needed.

5. **Launch backend**

   ```bash
   make dev
   ```

6. **Launch dashboard**

   ```bash
   make dashboard
   ```

7. **Trigger ingestion & classification**

   ```bash
   make ingest
   make classify
   ```

## API

| Endpoint       | Method | Description |
|----------------|--------|-------------|
| `/discover`    | POST   | Auto-discovers Reddit subreddits and YouTube channels mentioning configured products. |
| `/ingest`      | POST   | Pulls recent posts/comments for selected sources and products. |
| `/classify`    | POST   | Runs NLP classification and syncs vectors to Weaviate. |
| `/metrics`     | GET    | Sentiment distribution, voice share, aspects, and comparative metrics. |
| `/summary`     | GET    | Generates OpenAI summaries per product. |
| `/search`      | GET    | Semantic search across ingested comments. |
| `/news/seed`   | GET    | Returns seed topics/URLs for future news integrations. |
| `/health`      | GET    | Health check. |

## Testing & Quality

```bash
make test
make lint
```

## Deployment Notes

- The provided `Dockerfile` packages the FastAPI service for deployment (e.g., Azure Container Instances).
- Use `docker-compose` in production to provision Postgres + Weaviate managed services or containers.
- Future work: enable Lightpanda integration (`app/integrations/lightpanda.py`) and Lovable UI through `/metrics` and `/summary` JSON.

## Screenshots & Demo

- Run Streamlit locally via `make dashboard` to view the minimal UI.

## License

Internal prototype. Validate API usage against Reddit and YouTube Terms of Service before production deployment.
