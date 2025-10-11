#!/bin/bash
set -e -u -o pipefail

cd $(dirname $0)

export SEQGEN_ID_PREFIX="test-"
SEQGEN="python3 ../src/main.py"
RESULT=0

for input_file in *.seq; do
  echo $input_file
  output_file="${input_file%.*}.output.drawio"
  expected_file="${input_file%.*}.expected.drawio"

  $SEQGEN -i $input_file -o $output_file

  if ! diff $output_file $expected_file ; then
    RESULT=1
  fi
done

exit $RESULT
