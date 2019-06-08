import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pydiablo",
    version="0.0.3",
    author="youbetterdont",
    #author_email="author@example.com",
    description="A collection of Diablo 2 utilities.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/youbetterdont/pydiablo",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    install_requires=[
        "numpy>=1.15"
    ]
)
