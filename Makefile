.PHONY: dev test audit clean

dev:
	TEST_MODE=true python src/main.py

test:
	./run_all_20_layers.sh

audit:
	bash generate_audit_bundle.sh

clean:
	rm -rf __pycache__ .pytest_cache audit_reports/*.zip
