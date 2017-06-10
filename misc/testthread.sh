#!/bin/bash
echo "started at $(date +%s%3N)"
for i in $(seq 1 10); do
  curl "localhost:8080/$i$(date +%s%3N)" &
  curl "localhost:8080" -XPOST -d"$(date +%s)" &
  [[ $(($i % 2)) -eq 0 ]] && curl "localhost:8080" -XPOST -d"trunc" &
  [[ $(($i % 3)) -eq 0 ]] && curl "localhost:8080" -XPOST -d"trunc" &
done