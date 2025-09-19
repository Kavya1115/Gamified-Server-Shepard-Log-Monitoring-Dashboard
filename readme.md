# Gamified "Server Shepherd" Log Monitoring Dashboard

## Project Overview

### Introduction

This project transforms the typically dry task of server log monitoring into an engaging, visual, and intuitive "game." It provides an at-a-glance, metaphorical view of server health, making it easier to spot problems.

### Objectives

- **Stream log data** from a server to a central application in real-time.
- **Develop a web dashboard** that visualizes logs metaphorically (e.g., as a flock of sheep).
- **Enable real-time interaction** with the visualized logs.

### Scope

- **In-Scope:**  
    - Log-shipping agent  
    - Central processing server  
    - Web-based visualization dashboard for a single log type (e.g., NGINX access logs)

- **Out-of-Scope:**  
    - Historical log analysis  
    - Complex alerting rules  
    - Support for multiple log formats out of the box

---

## System Architecture & Technology

### High-Level Architecture

A lightweight Python "agent" on a server tails a log file and sends new lines to a central backend. The backend parses these logs and broadcasts structured data via WebSockets to the frontend, which updates a graphical simulation.

### Technology Stack

- **Log Agent:** Python (`watchdog` library)
- **Backend:** Python, FastAPI, WebSockets
- **Frontend:** React.js, p5.js or Three.js (for graphics)
- **DevOps:** Docker, Git

---

## Phase-by-Phase Implementation Plan

### Phase 1: Log Streaming

- **Agent:**  
    Write a simple Python script using the `watchdog` library to monitor a log file for changes. When a new line is added, the script sends it over a simple TCP socket.
- **Backend:**  
    Create a FastAPI application that listens on a TCP port to receive the raw log lines from the agent.
- **Deliverable:**  
    A functional agent-server pair where log lines written on the server are instantly printed to the console of the central application.

---

### Phase 2: Visualization Foundation

- **Backend:**  
    Parse the raw log lines into a structured JSON format (e.g., `{"status_code": 200, "ip": "1.2.3.4"}`). Set up a WebSocket endpoint to broadcast this JSON data.
- **Frontend:**  
    Build a React application using p5.js for the canvas. Connect to the backend WebSocket and, upon receiving a message, draw a simple shape (e.g., a green circle for a 200 status, a red one for 500).
- **Deliverable:**  
    A live dashboard where new log entries appear as colored circles in real time.

---

### Phase 3: Gamification and Interaction

- **Frontend:**  
    Replace the simple circles with "sheep" sprites. Give them simple animation, like wandering around a field. Make the red "error" sheep fall over.
- **Backend:**  
    Implement a simple API endpoint for "acknowledging" an error.
- **Frontend:**  
    Allow a user to click on a red sheep. This should display the full log message and have an "Acknowledge" button that calls the backend API. When acknowledged, the sheep could be visually "healed" or removed.
- **Deliverable:**  
    An interactive dashboard where users can not only see but also interact with the visualized server events.

---

### Phase 4: Polish and Deployment

- **Backend:**  
    Document the setup for the log agent and the API. Containerize the application using Docker.
- **Frontend:**  
    Refine the graphics and user interface. Add counters for total requests, error rates, etc.
- **Deliverable:**  
    A complete, deployed application that provides a novel and intuitive way to monitor server health.