dev:
	@echo "Run backend and frontend in two terminals:"
	@echo "1) cd apps/api && uvicorn nestiq.main:app --reload --port 8000"
	@echo "2) cd apps/web && npm run dev"
