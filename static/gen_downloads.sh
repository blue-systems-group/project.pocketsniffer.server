#!/bin/bash

for size in $@
do
    dd if=/dev/zero of=downloads/test-"$size"M.bin bs=1M count=$size
done
