# Makefile for Python Heuristic Detector Project

.PHONY: test clean install

# Run unit tests
test:
	@if [ ! -d ".venv" ]; then \
		echo ">>> Virtual environment not found. Please run ./install_linux.sh or install_windows.bat first."; \
		exit 1; \
	fi
	@.venv/bin/python3 -m unittest discover -s echo_node_system/echo_graph_flow_editor/heuristics/unit_tests -v

# Clean up pyc/cache files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -r {} +

# Install dependencies (Linux only; for Windows, use install_windows.bat)
install:
	bash install_linux.sh
