# Deployment Guide

## Local Development

`ash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
`

## Production Deployment (Ubuntu/Debian)

### Install dependencies
`ash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx
`

### Setup application
`ash
git clone https://github.com/Om1267/Hospital_Management.git
cd Hospital_Management
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
`

### Run with Gunicorn
`ash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
`

### Configure Nginx
Point your Nginx server block to http://127.0.0.1:8000.

## Environment Variables

See .env.example for required environment variables.
