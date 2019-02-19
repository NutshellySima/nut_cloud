import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='nut_cloud',
    version='19.02.19',
    author="Chijun Sima",
    author_email="simachijun@gmail.com",
    description="A website featuring a easy cloud drive and online shop.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NutshellySima/nut_cloud",
    packages=setuptools.find_packages(),
    license='MIT',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.7',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3',
    install_requires=[
        'flask',
        'zxcvbn',
        'PyNaCl',
        'hurry.filesize',
        'qrcode',
        'click',
        'markdown2',
        'Pillow',
    ],
)
