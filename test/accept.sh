#!/bin/bash
set -e -u -o pipefail

cd $(dirname $0)

export SEQGEN_ID_PREFIX="test-"
SEQGEN="python3 ../src/main.py"

for input_file in *.seq; do
  echo $input_file
  output_file="${input_file%.*}.output.drawio"
  expected_file="${input_file%.*}.expected.drawio"

  $SEQGEN -o $expected_file $input_file
done
