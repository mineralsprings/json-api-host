#!/bin/bash
for i in $(seq 1 10); do
  curl "localhost:8080/$i$(date +%s%3N)" &
  curl "localhost:8080" -d"$(date +%s)" &
done