from setuptools import setup, find_packages

setup(
    name="cdb",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "maxminddb",
        "netaddr",
    ],
    author="Kuzmin Rodion",
    author_email="r.kuzmin@crpt.ru",
    description="Library for mmdb data minimization",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.12",
)
