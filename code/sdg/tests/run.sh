#!/usr/bin/bash

set PYTHONPATH=/home/mihai/repos/tensor-contraction/sdg

RANKS=(50 100 150 200 250 300 350 400 450 500 550 600 650 700 750 800 850 900 950 1000)
#SIZES=(8 16 32 64 128 256 512 1024 2048 4096 8192 16384 32768 65536)
#SIZES=(500 1000 1500 2000 2500 3000 3500 4000 4500 5000 5500 6000 6500 7000 7500 8000 8500 9000 9500 10000)
#SIZES=(248 512 1024 2048 4096 8192 16384 32768 65536 131072 262144 524288 1048576 2097152 4194304 8388608 16777216 33554432 67108864 134217728 268435456)

for r in "${RANKS[@]}"; do
  python sdg_test.py --processors $r --einsum 'ij,jk->ik' --iterationSpace 1024,1024,1024 > __rerunthicc_MMM_$r.txt
  #python sdg_test.py --processors $s --einsum 'ijk,kl,jl->il' --iterationSpace 2048,10,10,2048 > __newskinny_mttkrp_$s.txt
done
