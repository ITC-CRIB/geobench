from setuptools import setup, find_packages

# Function to read the requirements.txt file and return the list of dependencies
def read_requirements():
    with open('requirements.txt') as req:
        return req.read().splitlines()

setup(
    name='geobench',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'geobench=geobench.main:main',
        ],
    },
    install_requires=read_requirements(),
)