#!/bin/sh
#
# Generic python environment for OpenFIDO
#

export OPENFIDO_INPUT=$PWD/autotest
export OPENFIDO_OUTPUT=$PWD/autotest/output
mkdir -p $OPENFIDO_OUTPUT
rm -rf $OPENFIDO_OUTPUT/{*,.??*}

echo '*** INPUTS ***'
ls -l $OPENFIDO_INPUT

python3 openfido.py

echo '*** OUTPUTS ***'
ls -l $OPENFIDO_OUTPUT

echo '*** END ***'

