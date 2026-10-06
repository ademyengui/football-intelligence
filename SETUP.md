# Football Intelligence Dashboard - Setup Guide

## 1. System Dependencies (Requires `sudo`)

Run the following commands on Ubuntu 24 to install required packages and start services:

```bash
# 1. Install system packages
sudo apt update
sudo apt install -y postgresql redis-server python3-venv python3-dev libpq-dev ffmpeg

# 2. Start and enable PostgreSQL and Redis services
sudo systemctl start postgresql redis-server
sudo systemctl enable postgresql redis-server

# 3. Provision PostgreSQL user and database
sudo -u postgres psql -c "CREATE USER football WITH PASSWORD 'football';"
sudo -u postgres psql -c "CREATE DATABASE football OWNER football;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE football TO football;"
```

## 2. Environment Configuration

Copy the example environment configuration:

```bash
cp .env.example .env
```

## 3. Backend Setup

Initialize Python virtual environment and install dependencies:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

Run database migrations:

```bash
make migrate
```

## 4. Frontend Setup

Install Angular frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

## 5. Development Server

Start all services (API, RQ worker, Frontend):

```bash
make dev
```
