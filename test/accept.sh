#!/bin/bash
set -e -u -o pipefail

cd $(dirname $0)

SEQGEN="python ../src/main.py"

for input_file in *.seq; do
  echo $input_file
  output_file="${input_file%.*}.output.drawio"
  expected_file="${input_file%.*}.expected.drawio"

  $SEQGEN -i $input_file -o $expected_file
done
