#!/bin/bash

pip install --upgrade pip
pip install nose
pip install cython
pip install numpy
pip install pandas
pip install git+https://github.com/dalejung/asttools
pip install -e git+https://github.com/dalejung/earthdragon#egg=earthdragon
pip install .

pip freeze
