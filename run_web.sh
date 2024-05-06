#!/bin/bash
./venv/bin/gunicorn --capture-output --bind 0.0.0.0:8000 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app
