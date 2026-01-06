#!/bin/bash
export PYTHONPATH=..
gunicorn --bind=0.0.0.0:8000 --timeout 600 src.app:app
