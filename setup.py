from setuptools import setup, find_packages

VERSION = "0.0.1"
DESCRIPTION = "DRFI remove background filter for thumbor"
LONG_DESCRIPTION = (
    "Install DRFI model as a filter to remove background to use in thumbor"
)

require_packages = ["pillow", "numpy"]

setup(
    name="drfi",
    version=VERSION,
    author="Hop Bui",
    author_email="vanhop3499@gmail.com",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    include_package_data=True,
    install_requires=require_packages,
    keywords=["drfi thumbor"],
)
