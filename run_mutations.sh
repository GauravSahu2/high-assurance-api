#!/bin/bash
set -e

export TEST_MODE="true"
export JWT_SECRET="super-secure-dev-secret-key-12345"
export PYTHONPATH=src

echo "📄 Copying schema into mutants layout..."
mkdir -p mutants/src
cp src/openapi.yaml mutants/src/openapi.yaml

export MUTMUT_TESTING="true"
echo "🧬 Unleashing the Mutation Engine..."
mutmut run

echo "✅ Mutation run complete. Generating HTML report..."
mutmut results
