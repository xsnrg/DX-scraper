#!/bin/bash
PYTHONPATH=. uvicorn src.api:app --reload