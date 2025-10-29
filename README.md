## Dockerfile AI Optimizer (Beta) (Web UI + CLI) by [Alexander Serzhankou](https://www.linkedin.com/in/aliaksandr-serzhankou/)

### Demo

Web UI is available live at [https://docker-ai-optimizer.onrender.com](https://docker-ai-optimizer.onrender.com/)

### Setup

1. Create and activate a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Set Abacus.AI credentials (can be used with OpenAI as well after modifications)

```bash
export ABACUS_API_KEY=*** # Bearer token for routellm (required)
export ABACUS_MODEL=gpt-5-mini   # defaults to gpt-5 (optional)
```

### Web UI

Run the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/` and paste your Dockerfile. The server exposes:

- `GET /healthz` – health check
- `POST /api/optimize` – accepts `{ "dockerfile": "..." }`

### CLI Usage

```bash
# Basic usage - read file, output to stdout
python cli.py -i Dockerfile

# Read file, write to output file
python cli.py -i Dockerfile -o optimized.Dockerfile

# Read from stdin, output to stdout
cat Dockerfile | python cli.py

# Force output to stdout even with -o
python cli.py -i Dockerfile -o /dev/stdout

# Use different model
python cli.py -i Dockerfile --model gpt-4o-mini

# Override API key
python cli.py -i Dockerfile --api-key your_key_here
```

### Notes

- **Web UI**: Static page with dark Material theme, shows optimization summary
- **CLI**: Command-line tool for automation, outputs only the optimized Dockerfile
- Both use Abacus.AI ChatLLM REST endpoint (`/v1/chat/completions`) via `requests`
- Configure `ABACUS_API_KEY`; optionally `ABACUS_MODEL`

