import os
from setuptools import setup, find_packages

setup(
    name='asciicast2gif',
    description='Converts AsciiCast terminal recordings to animated GIFs',
    url='https://github.com/trailofbits/asciicast2gif',
    author='Trail of Bits',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.6',
    install_requires=[
        'Pillow>=5.3.0'
    ],
    entry_points={
        'console_scripts': [
            'asciicast2gif = asciicast2gif.__main__:main'
        ]
    }
)
