#!/bin/bash
set -e -u -o pipefail

cd $(dirname $0)

export SEQGEN_ID_PREFIX="doc-"
SEQGEN="python3 ../src/main.py"

for input_file in *.seq; do
  echo $input_file
  drawio_file="${input_file%.*}.drawio"
  image_file="${input_file%.*}.png"

  $SEQGEN --output $drawio_file $input_file
  drawio --export --output $image_file $drawio_file
done
