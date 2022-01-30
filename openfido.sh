#!/bin/sh
#
# Generic python environment for OpenFIDO
#

error()
{
    echo '*** ABNORMAL TERMINATION ***'
    echo 'See error Console Output stderr for details.'
    echo "See https://github.com/openfido/loadshape for help"
    exit 1
}

trap on_error 1 2 3 4 6 7 8 11 13 14 15

set -x # print commands
set -e # exit on error
set -u # nounset enabled

if [ ! -f "$OPENFIDO_INPUT/config.csv" ]; then
    echo "*** MISSING REQUIRED INPUT ***"
    error
fi

export DEBIAN_FRONTEND=noninteractive
apt-get -q -y update > /dev/null
apt-get -q -y install python3 python3-pip > /dev/null
python3 -m pip install -q -r requirements.txt > /dev/null

echo '*** INPUTS ***'
ls -l $OPENFIDO_INPUT

python3 openfido.py || error

echo '*** OUTPUTS ***'
ls -l $OPENFIDO_OUTPUT

echo '*** RUN COMPLETE ***'
echo 'See Data Visualization and Artifacts for results.'

echo '*** END ***'

