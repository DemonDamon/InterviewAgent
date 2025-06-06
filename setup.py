from setuptools import setup, find_packages

setup(
    name="interview-agent",
    version="1.0.0",
    description="AI-powered interview agent system",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.8.0,<2.0.0",
        "python-multipart>=0.0.5",
        "python-dotenv>=0.19.0",
        "requests>=2.25.0",
        "pymilvus>=2.3.0",
        "qdrant-client>=1.6.0",
        "numpy>=1.21.0",
        "sentence-transformers>=2.2.0",
    ],
) 