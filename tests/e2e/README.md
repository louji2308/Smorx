# End-to-end tests

Full-agent journey tests that drive the system from task intake through
verification and certification. These require the FastAPI backend
(``apps/api``) to be running locally.

Run:
```bash
# Start the API first
uvicorn app.main:create_app --factory --app-dir apps/api --port 8765

# Then run the tests
python -m pytest tests/e2e -q
```