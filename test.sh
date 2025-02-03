#!/bin/bash
set -e  # stop on the 1st error
pyright
ruff check . --fix
poetry run pytest --exitfirst