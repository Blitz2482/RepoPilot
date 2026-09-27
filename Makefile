backend-test:
	cd backend && pytest -q

backend-run:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

verify-backend:
	python -m compileall -q backend
	pytest -q backend

verify-deployment:
	python scripts/verify_deployment.py
	node scripts/verify_frontend_config.mjs
	node scripts/verify_frontend_syntax.mjs

verify: verify-backend verify-deployment

release-verify:
	python scripts/release_verify.py

verify-production-env:
	python scripts/verify_production_env.py

verify-live:
	@echo "Usage: python scripts/verify_live_deployment.py https://<backend> --repo https://github.com/owner/repo"
