# Python Heuristic Detector

A high-reliability heuristic-based Python code detector and sanitizer for text and JSON data extracted from the NeuroGenesys Framework.

This module is currently integrated as an operational node within NeuroGenesys' node-based graph editor. It is specifically designed to reliably detect, isolate, and wrap Python code segments embedded within arbitrary textual or JSON data.

In practice, this node processes user prompts, allowing the associated Large Language Model (LLM)—equipped with a suitably defined system prompt—to efficiently delegate wrapped Python code segments to specialized sub-agents or routing systems. This strategy optimizes the use of the LLM's context window, significantly reducing computational overhead in the finalized framework.

Furthermore, the module can also be strategically employed as a post-processing node following LLM-generated outputs. This facilitates streamlined indexing, subsequent automated processing, and additional context economy optimizations.

Note: The NeuroGenesys Framework remains under active development, and features described herein may evolve.

## Project Structure

```
echo_node_system/
├── main.py
└── echo_graph_flow_editor/
    └── heuristics/
        ├── __init__.py
        ├── python_heuristic_detector.py
        └── unit_tests/
            ├── __init__.py
            └── test_python_heuristics.py
Documentation/
├── algo_pseudo_code.md
└── PythonHeuristicDetector_Final_simplified_organigram.svg
```

- **main.py**: A small PyQt-based program providing a graphical interface to input text and see heuristic detection results live as the text changes.
- **python_heuristic_detector.py**: Main implementation of the heuristic detector.
- **test_python_heuristics.py**: Comprehensive unit tests using `unittest`.


## Features

- Detects Python code in free text or JSON structures.
- Supports dangerous code pattern recognition (e.g., `os.system`, `eval`, `pickle.loads`).
- Handles nested JSON with optional parallel processing.
- Adjustable confidence threshold for wrapping decisions.
- Fully thread-safe implementation using `QMutex` and `QMutexLocker`.
- Minimal dependencies (only `qtpy` and `PyQt5`).

## Requirements

- Python 3.8 or higher
- qtpy
- PyQt5

## Setup Instructions

This project uses a Python virtual environment to isolate dependencies.

### 1. Preparing the environment

On Linux/macOS:

```bash
bash install_linux.sh
```

On Windows:

```cmd
install_windows.bat
```

This script will:
- Create a virtual environment in the `.venv/` folder
- Upgrade `pip`
- Install all required packages (`qtpy`, `PyQt5`)

After successful setup, the environment is ready for use.

### 2. Activating the environment

On Linux/macOS:

```bash
source .venv/bin/activate
```

On Windows:

```cmd
call .venv\Scripts\activate.bat
```

### 3. Running the tests

Once the virtual environment is activated, you can run the unit tests using:

```bash
make test
```

This command will:
- Ensure that the virtual environment exists
- Use `.venv/bin/python3` to run all unit tests in `echo_node_system/echo_graph_flow_editor/heuristics/unit_tests/`
- Display a detailed test report

You can also manually run:

```bash
python -m unittest discover -s echo_node_system/echo_graph_flow_editor/heuristics/unit_tests/ -v
```

However, `make test` is preferred for consistency.

### 4. Cleaning the project

To remove all Python cache files (`.pyc`, `__pycache__`) and reset the workspace:

```bash
make clean
```

## Usage Example

```python
from echo_node_system.echo_graph_flow_editor.heuristics.python_heuristic_detector import PythonHeuristicDetector

detector = PythonHeuristicDetector()
text = "def greet():\n    print('Hello')"
wrapped_text = detector.detectPythonInString(text)
print(wrapped_text)
```

## Documentation

- **Algorithm Pseudo-Code:** [Documentation/algo_pseudo_code.md](Documentation/algo_pseudo_code.md)
- **Simplified Organigram:** [Documentation/PythonHeuristicDetector_Final_simplified_organigram.svg](Documentation/PythonHeuristicDetector_Final_simplified_organigram.svg)

Both resources offer insights into the internal workings of the heuristic detector.


## Author

This project was developed by **LoganSeven**.

## License

This project is licensed under the [MIT (modified) License](LICENSE).

## Final Note

Researchers, security experts, and enthusiasts are **strongly encouraged** to attempt to **defeat, fuzz, and challenge** the heuristic detection system.

Feedback, reports, and contributions are **highly welcome** to continually improve its resilience and reliability.
