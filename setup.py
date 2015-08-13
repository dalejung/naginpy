from setuptools import setup

DISTNAME='naginpy'
FULLVERSION='0.1-dev'

setup(
    name=DISTNAME,
    version=FULLVERSION,
    packages=['naginpy'],
    install_requires = [
        'asttools',
        'earthdragon',
    ],
    url='http://github.com/dalejung/naginpy/',
    license='BSD',
    author='Dale Jung',
    author_email='dale@dalejung.com',
)
