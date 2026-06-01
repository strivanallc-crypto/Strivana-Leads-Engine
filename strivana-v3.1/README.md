# Strivana v3.1

Sovereign, open-source data pipeline for lead generation with identity-first extraction and heuristic-first scoring.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      STRIVANA V3.1 PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │   DDGS   │───▶│ Parallel Crawl   │───▶│ Identity Extraction │   │
│  │  Search  │    │ (Crawlee+Crawl4AI)│    │ (JSON-LD → Regex)   │   │
│  └──────────┘    └──────────────────┘    └─────────────────────┘   │
│                                              │                       │
│                                              ▼                       │
│  ┌──────────┐    ┌──────────────────┐    ┌─────────────────────┐   │
│  │ GHL Push │◀───│ Heuristic Score  │◀───│ Intent Detection    │   │
│  │          │    │ (Model Swipe)    │    │ (Regex Signals)     │   │
│  └──────────┘    └──────────────────┘    └─────────────────────┘   │
│         ▲                  │                                       │
│         │                  ▼                                       │
│         │          ┌──────────────────┐                           │
│         └──────────│ LLM Fallback     │                           │
│                    │ (deepseek-chat)  │                           │
│                    │ confidence < 0.3 │                           │
│                    └──────────────────┘                           │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Principles

1. **Identity-First**: Extract name/title/email first, phone second
2. **Model Swipe Router**: Heuristic-first routing, LLM only on low-confidence fallback
3. **Zero Token Bleed**: Replace all `deepseek-reasoner` scoring/pushing with rule-based logic
4. **Graceful Degradation**: Missing fields never break the pipeline
5. **Async-Native**: Async where I/O bound, synchronous where CPU-bound

## Setup

### Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional)
- GoHighLevel API token
- Hermes job scheduler (optional)

### Local Installation

```bash
# Clone repository
cd strivana-v3.1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GHL_TOKEN and LOCATION_ID

# Run pipeline
./scripts/run_pipeline.sh
```

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f strivana-v3.1

# Stop
docker-compose down
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
GHL_TOKEN=your_gohighlevel_api_token
LOCATION_ID=your_gohighlevel_location_id
TARGETS_FILE=config/targets.txt
LOG_LEVEL=INFO
```

### Target URLs

Add target URLs to `config/targets.txt`:

```
https://example.com
https://company.com/about
https://startup.io/team
```

## Hermes Integration

### Enable v3.1 Jobs

```bash
# Stop old jobs (prevent token bleed)
./scripts/stop_bleeding.sh

# Enable v3.1 pipeline
hermes enable strivana-v3.1-pipeline
hermes enable strivana-v3.1-healthcheck

# Verify jobs
hermes list
```

### Job Schedule

| Job | Schedule | Description |
|-----|----------|-------------|
| `strivana-v3.1-pipeline` | Every 6 hours | Main lead extraction pipeline |
| `strivana-v3.1-healthcheck` | Every 30 minutes | Health monitoring |
| `strivana-v3.1-log-rotation` | Daily at midnight | Log cleanup |

## Model Swipe Explanation

The Model Swipe Router implements confidence-based routing:

```python
if confidence >= 0.3:
    # Use fast heuristic methods
    route_to_heuristic()
else:
    # Fall back to LLM (deepseek-chat)
    route_to_llm()
```

### Scoring Breakdown

| Signal | Points |
|--------|--------|
| Decision maker title (CEO/Founder/VP/Director) | +40 |
| Valid email address | +30 |
| Valid phone number | +20 |
| Company size >10 (heuristic) | +10 |
| Intent signals (variable) | +0-20 |

### Confidence Thresholds

| Score Range | Confidence | Action |
|-------------|------------|--------|
| 70-100 | 0.9 | High confidence, push to GHL |
| 50-69 | 0.6 | Medium confidence, push to GHL |
| 30-49 | 0.4 | Low confidence, push to GHL |
| 0-29 | 0.2 | Very low, trigger LLM fallback |

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_identity_extractor.py -v

# Run with coverage
pytest --cov=src tests/
```

## Monitoring

### Logs

Logs are stored in `logs/` directory:

```bash
# View recent logs
tail -f logs/pipeline.log

# Search for errors
grep "ERROR" logs/pipeline.log
```

### Metrics

Key metrics to monitor:

- Leads extracted per URL
- Success rate of GHL pushes
- Heuristic vs LLM routing ratio
- Average confidence scores

## Troubleshooting

### Common Issues

**No leads extracted:**
- Check if target URLs have JSON-LD Person schemas
- Verify regex patterns match site format
- Check for anti-bot protections

**GHL push failures:**
- Verify GHL_TOKEN is valid
- Check LOCATION_ID is correct
- Review rate limit handling in logs

**High LLM fallback rate:**
- Review identity extraction quality
- Adjust confidence threshold in `model_swipe.py`
- Check email/phone validation patterns

## License

MIT License - See LICENSE file for details.

## Version History

- **v3.1** (Current): Parallel crawling, model swipe router, zero token bleed
- **v3.0**: Initial autonomous pipeline
- **v2.x**: Legacy collect/score/push architecture
