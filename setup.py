"""
Setup script para Kinect Table System
======================================
"""

from setuptools import setup, find_packages
from pathlib import Path

# Leer el README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Leer requirements
requirements = (this_directory / "requirements.txt").read_text(encoding="utf-8").splitlines()
# Filtrar comentarios y líneas vacías
requirements = [r.strip() for r in requirements if r.strip() and not r.startswith("#")]

setup(
    name="kinect-table-system",
    version="0.1.0",
    author="Tu Nombre",
    author_email="tu-email@ejemplo.com",
    description="Sistema de reconocimiento de objetos y gestos con Kinect Xbox 360",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tu-usuario/kinect_table_system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8,<3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "kinect-table=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
