#!/bin/sh
#
# Generic python environment for OpenFIDO
#
# To run the test
#
#   $ sh autotest.sh
#

set -e
set -x
set -p

INPUTS=$(ls -1d $PWD/autotest/input_*)
for INPUT in ${INPUTS// /\\ /}; do
	echo Processing $INPUT...
	export OPENFIDO_INPUT="$INPUT"
	export OPENFIDO_OUTPUT=${INPUT/input_/output_}
	mkdir -p $OPENFIDO_OUTPUT
	rm -rf $OPENFIDO_OUTPUT/{*,.??*}

	echo '*** INPUTS ***'
	ls -l $OPENFIDO_INPUT

	python3 openfido.py

	echo '*** OUTPUTS ***'
	ls -l $OPENFIDO_OUTPUT

	echo '*** END ***'
done