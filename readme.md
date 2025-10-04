# 🐑 Server Shepherd - Gamified Log Monitoring Dashboard

A fun and engaging way to monitor server logs by visualizing them as a flock of sheep in a virtual field. Watch your server health come to life with animated sheep that represent different types of log entries!

## 🌟 Features

- **Real-time Log Monitoring**: Stream logs from your server in real-time
- **Gamified Visualization**: Logs appear as animated sheep in a virtual field
- **Interactive Dashboard**: Click on error sheep to view details and acknowledge issues
- **Live Statistics**: Track success rates, error counts, and system health
- **Beautiful UI**: Modern, responsive interface with smooth animations

## 🏗️ Architecture

```
┌─────────────────┐    TCP     ┌─────────────────┐    WebSocket    ┌─────────────────┐
│   Log Agent     │ ──────────►│   Backend       │ ──────────────► │   Frontend      │
│   (Python)      │            │   (FastAPI)     │                 │  (React + p5.js)│
└─────────────────┘            └─────────────────┘                 └─────────────────┘
```

- **Log Agent**: Python script using `watchdog` to monitor log files
- **Backend**: FastAPI server with WebSocket support for real-time communication
- **Frontend**: React application with p5.js for canvas-based animations

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional)

### Option 1: Docker Compose (Recommended)

1. **Clone and start the services:**
   ```bash
   git clone <repository-url>
   cd server-shepherd
   docker-compose up --build
   ```

2. **Access the dashboard:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Option 2: Manual Setup

1. **Backend Setup:**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   
   # Start the backend
   python backend.py
   ```

2. **Frontend Setup:**
   ```bash
   # Install Node.js dependencies
   npm install
   
   # Start the frontend
   npm start
   ```

3. **Log Agent Setup:**
   ```bash
   # Generate sample logs
   python sample_log_generator.py sample.log 1
   
   # In another terminal, start the log agent
   python log_agent.py sample.log localhost 9999
   ```

## 🎮 How to Use

### The Dashboard

1. **Sheep Visualization**: Each log entry appears as a sheep in the field
   - 🟢 **Green Sheep**: Successful requests (200-399 status codes)
   - 🔴 **Red Sheep**: Error requests (400+ status codes)
   - 🟡 **Yellow Sheep**: Healed/acknowledged errors

2. **Interactive Features**:
   - Click on red (error) sheep to view log details
   - Acknowledge errors to "heal" the sheep
   - Clear all sheep to reset the field
   - View real-time statistics in the sidebar

3. **Statistics Panel**:
   - Total log count
   - Success/error counts
   - Error rate percentage
   - Connection status

### Monitoring Your Own Logs

To monitor your own log files:

```bash
# Start the backend first
python backend.py

# Then start the log agent pointing to your log file
python log_agent.py /var/log/nginx/access.log localhost 9999
```

The system currently supports NGINX access log format. The backend automatically parses:
- IP addresses
- HTTP methods and paths
- Status codes
- Response sizes
- User agents

## 🔧 Configuration

### Backend Configuration

The backend runs on:
- **HTTP API**: Port 8000
- **TCP Log Receiver**: Port 9999
- **WebSocket**: ws://localhost:8000/ws

### Log Agent Configuration

```bash
python log_agent.py <log_file_path> [backend_host] [backend_port]
```

Example:
```bash
python log_agent.py /var/log/nginx/access.log localhost 9999
```

## 📊 API Endpoints

- `GET /` - Basic info and health check
- `GET /stats` - Current statistics
- `GET /logs` - Recent log entries
- `POST /acknowledge` - Acknowledge an error
- `WebSocket /ws` - Real-time log stream

## 🐳 Docker Services

- **backend**: FastAPI server with WebSocket support
- **frontend**: React application served by nginx
- **log-agent**: Monitors log files and sends data to backend
- **log-generator**: Generates sample logs for testing

## 🎨 Customization

### Adding New Log Formats

To support additional log formats, modify the `parse_nginx_log()` function in `backend.py`:

```python
def parse_custom_log(log_line: str) -> Dict[str, Any]:
    # Your custom parsing logic here
    return {
        "status_code": 200,
        "ip": "127.0.0.1",
        "method": "GET",
        "path": "/",
        # ... other fields
    }
```

### Customizing Sheep Behavior

Modify the sheep animation logic in `src/App.js`:

```javascript
const createSheep = (logData) => {
    // Customize sheep properties
    const newSheep = {
        // ... existing properties
        customProperty: "value"
    };
};
```

## 🛠️ Development

### Project Structure

```
server-shepherd/
├── backend.py              # FastAPI backend server
├── log_agent.py            # Log monitoring agent
├── sample_log_generator.py # Sample log generator
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
├── src/
│   ├── App.js             # Main React component
│   ├── index.js           # React entry point
│   └── index.css          # Styles
├── public/
│   └── index.html         # HTML template
├── Dockerfile.backend     # Backend Docker image
├── Dockerfile.frontend    # Frontend Docker image
└── docker-compose.yml     # Docker services
```

### Running Tests

```bash
# Backend tests
python -m pytest tests/

# Frontend tests
npm test
```

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Visualizations powered by [p5.js](https://p5js.org/)
- Frontend built with [React](https://reactjs.org/)
- Log monitoring with [watchdog](https://python-watchdog.readthedocs.io/)

---

**Happy Monitoring! 🐑✨**
