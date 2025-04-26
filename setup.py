from setuptools import setup, find_packages

setup(
    name="python-heuristic-detector",
    version="0.1.0",
    description="A heuristic-based Python code detector for text and JSON",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "qtpy",
    ],
    python_requires=">=3.8",
)