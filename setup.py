import os
from setuptools import setup, find_packages

setup(
    name='cast2gif',
    description='Converts AsciiCast terminal recordings to animated GIFs',
    url='https://github.com/trailofbits/cast2gif',
    author='Trail of Bits',
    version='0.0.2',
    packages=find_packages(),
    package_data={'cast2gif': [os.path.join('Source_Code_Pro', '*')]},
    include_package_data=True,
    python_requires='>=3.6',
    install_requires=[
        'Pillow>=5.3.0'
    ],
    entry_points={
        'console_scripts': [
            'cast2gif = cast2gif.__main__:main'
        ]
    }
)
