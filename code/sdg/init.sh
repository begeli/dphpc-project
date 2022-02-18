#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo $DIR
export PYTHONPATH="$DIR"/dace:"$DIR"/daceml
export ORT_RELEASE="$DIR"/ONNX/onnxruntime_dist
cd daceml
mlBranch=`git rev-parse --abbrev-ref HEAD`
if [ "$mlBranch" == lenet5 ]; then
    echo "daceml is already setup"
else
    echo "Setting up daceml..."
    git checkout lenet5
    pip3 install -e .
fi
cd ../
