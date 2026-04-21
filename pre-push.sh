#!/bin/bash
export PYTHONPATH=src
export TEST_MODE=true
pytest -v -x && mutmut run --limit 20
