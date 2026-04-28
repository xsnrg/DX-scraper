# DXpedition Monitor

A real-time monitoring tool for tracking active DXpeditions across various radio amateur data sources. It aggregates data from multiple sources including DX Summit, DX Cluster, and DX News, providing a unified view of current active stations, their locations, and operating frequencies.

## 🚀 Features

- **Multi-Source Aggregation**: Pulls data from DX Summit, DX Cluster, and other amateur radio feeds.
- **Real-time Monitoring**: Provides current status of active stations and their target bands/modes.
- **QRZ QSO Integration**: Import your QRZ.com logbook, filter stations by your QSO history, and highlight matches.
- **Web Dashboard**: A simple, clean interface to view current DX activity.
- **REST API**: Easy integration via a FastAPI backend.
- **CLI Tool**: A command-line interface for quick checks and JSON/Table output.
- **Flexible Configuration**: Adjustable data staleness thresholds and source enabling/disabling.

## 🛠️ Architecture

- **Backend**: FastAPI / Python 3.12+
- **Data Fetchers**: Asynchronous fetchers utilizing `aiohttp` and `BeautifulSoup4`.
- **Frontend**: Static HTML/JS dashboard served directly by the API.
- **Configuration**: Environment-based configuration via `.env`.

## 📦 Installation

### Local Development

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd DXscraper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   Create a `.env` file in the root directory:
   ```env
   DXPEDITION_MAX_AGE_SECONDS=3600
   DXPEDITION_REQUEST_TIMEOUT=30
   DXPEDITION_RETRY_ATTEMPTS=3
   DXPEDITION_RETRY_DELAY_SECONDS=1.0
   ```

4. **Run the Web API**:
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   uvicorn src.api:app --reload
   ```
   Access the dashboard at `http://localhost:8000`.

5. **Run the CLI Tool**:
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   python src/main.py --format table
   ```

### Docker Deployment

The project is fully containerized for easy deployment.

1. **Build the image**:
   ```bash
   docker build -t dx-scraper .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 dx-scraper
   ```

3. **Run with custom configuration**:
   ```bash
   docker run -p 8000:8000 -e DXPEDITION_MAX_AGE_SECONDS=7200 dx-scraper
   ```

## 🧪 Testing

The project uses `pytest` for comprehensive testing.

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
export PYTHONPATH=$PYTHONPATH:.
pytest
```

## 💻 API Endpoints

- `GET /`: Serves the web dashboard.
- `GET /data`: Returns a JSON summary of current DXpeditions.
- `GET /qrz-status`: Returns QRZ credentials status.
- `POST /qrz-token`: Stores QRZ.com API credentials.
- `GET /qrz-sync`: Syncs QRZ logbook data.
- `GET /qrz-cache`: Returns cached QRZ QSO data.

## 📜 License

This project is licensed under the MIT License.
