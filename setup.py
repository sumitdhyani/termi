from setuptools import setup, find_packages

setup(
    name="termi",
    version="1.0.0",
    description="AI-powered terminal command helper",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "openai>=1.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "pyperclip>=1.8.0",
        "psutil>=5.9.0",
        "pydantic>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "termi=main:main",
        ],
    },
)
