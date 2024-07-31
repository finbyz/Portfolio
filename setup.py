from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in investment_portfolio/__init__.py
from investment_portfolio import __version__ as version

setup(
	name="investment_portfolio",
	version=version,
	description="Investment Portfolio",
	author="FinByz",
	author_email="info.finbyz.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
