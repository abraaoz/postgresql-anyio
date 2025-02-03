from setuptools import setup

with open("pganyio/_version.py") as f:
    exec(f.read())

test_dependencies = [
    "pytest==7.1.1",
    "pytest-trio==0.7.0",
    "coverage==6.3.2",
    "coverage-badge==1.1.0",
]

dev_dependencies = test_dependencies + [
    "wheel",
    "twine==4.0.0",
]

setup(
    name="pganyio",
    version=__version__,
    description="An AnyIO (asyncio or trio backend) PostgreSQL client library",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="http://github.com/elektito/pganyio",
    author="Mostafa Razavi",
    author_email="mostafa@sepent.com",
    license="MIT",
    packages=["pganyio"],
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "anyio==4.8.0",
        "python-dateutil==2.9.0",
        "orjson==3.6.8",
        "parsimonious==0.9.0",
    ],
    extras_require={
        "test": test_dependencies,
        "dev": dev_dependencies,
    },
)
