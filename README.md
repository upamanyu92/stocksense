# StockSense

StockSense is a modular, production-ready platform for stock prediction, analysis, and monitoring. It is designed for data scientists, quantitative analysts, and developers who need a robust, extensible system for building, deploying, and monitoring stock market models at scale.

## 🚀 NEW: Agentic Prediction System

StockSense now features an **intelligent agentic prediction system** that autonomously makes high-accuracy predictions through multi-agent collaboration:

- **🤖 Multi-Agent Architecture**: Specialized agents work together (Data Enrichment, Ensemble, Adaptive Learning)
- **📈 Enhanced Accuracy**: Ensemble methods combine Transformer + LSTM models with adaptive weighting
- **🧠 Self-Learning**: Continuously improves from prediction errors and adapts to market conditions
- **🎯 Confidence Scoring**: Every prediction includes confidence levels and uncertainty quantification
- **🔄 Market Regime Detection**: Automatically adapts strategies for bull/bear/sideways/volatile markets
- **✅ Autonomous Decisions**: Makes intelligent accept/caution/reject decisions on predictions

[Read Full Documentation →](docs/AGENTIC_SYSTEM.md)

## Purpose & Need

Modern financial markets generate vast amounts of data, and actionable insights require advanced analytics, automation, and reliable infrastructure. StockSense addresses these needs by providing:

- **Automated Data Ingestion:** Fetches and stores stock quotes in a local database, supporting batch and scheduled operations.
- **Modular Prediction Pipeline:** Easily plug in new models or update existing ones for stock price prediction.
- **Batch & Real-Time Processing:** Supports both batch predictions and real-time monitoring of model performance.
- **Monitoring & Transparency:** Built-in logging, monitoring, and status streaming for all major operations.
- **Extensibility:** Designed for easy integration with new data sources, models, and deployment environments.

## Key Features
- **Flask Web Dashboard:** Interactive dashboard for triggering predictions, fetching quotes, and viewing results.
- **Typeahead Search:** Fast, user-friendly search for stock quotes with autocomplete suggestions.
- **Batch Prediction:** Parallelized batch processing for efficient model inference.
- **Model Monitoring:** Track and log model performance and prediction outcomes.
- **Dockerized Deployment:** Ready for production with Docker and Docker Compose support.
- **PEP8 Compliant:** Clean, maintainable codebase.

## Project Structure
- `app/` - Core application logic (database, features, models, services, utils)
- `scripts/` - Utility and management scripts (DB setup, schedulers, etc.)
- `docker/` - Dockerfiles and deployment configuration
- `templates/` - HTML templates for the dashboard
- `static/` - Static assets (CSS, JSON, etc.)
- `.env` - Environment variables

## Setup & Usage
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Set up environment variables:**
   - Copy `.env.example` to `.env` and edit as needed.
3. **Initialize the database:**
   - Run scripts from `scripts/` (e.g., `python scripts/create_db.py`).
4. **Generate SSL certificates (for HTTPS):**
   - For development with self-signed certificates:
     ```bash
     python scripts/generate_ssl_cert.py
     ```
   - For production, obtain certificates from a trusted CA (e.g., Let's Encrypt)
   - To disable SSL and use HTTP only, set `USE_SSL=false` in your environment
5. **Start the application:**
   - For local development:
     ```bash
     python -m app.main
     ```
   - For production (Docker):
     ```bash
     docker compose up --build
     ```
6. **Access the dashboard:**
   - Visit `https://localhost:5005` (or your configured port).
   - For self-signed certificates, your browser will show a security warning - you can safely proceed in development by accepting the certificate.

## Security Notes
- **Development**: The app generates self-signed SSL certificates automatically. Your browser will show a security warning, which you can safely bypass in development.
- **Production**: Always use certificates from a trusted Certificate Authority (CA) like Let's Encrypt for production deployments.
- **Disable SSL**: Set `USE_SSL=false` environment variable to disable HTTPS and use HTTP (not recommended for production).
- **Detailed SSL Guide**: See [docs/SSL_SETUP.md](docs/SSL_SETUP.md) for comprehensive HTTPS/SSL configuration instructions.

## Extending StockSense
- **Add new models:** Place model code in `app/models/` and update the prediction pipeline.
- **Integrate new data sources:** Extend `app/db/` and `app/features/` as needed.
- **Customize the dashboard:** Edit templates in `app/templates/` and static assets in `app/static/`.

## Contributing
Pull requests are welcome! Please follow the code style (PEP8) and project structure. For major changes, open an issue first to discuss your ideas.

## License
MIT License (see LICENSE file)

---

StockSense empowers you to build, deploy, and monitor stock prediction models with confidence and transparency, whether for research, trading, or education.
