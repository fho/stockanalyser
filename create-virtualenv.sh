#!/bin/bash -e

virtualenv -p /usr/bin/python3.5 venv
source venv/bin/activate 
pip install money pytest pep8 pylint lxml requests

echo "Switch to Virtualenv with: 'source venv/bin/activate'"
