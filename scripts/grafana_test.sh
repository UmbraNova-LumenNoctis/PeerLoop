#!/bin/bash

# for i in {1..10000000}; do
#   curl -k -X GET https://localhost:8443/metrics
# done

for i in {1..10000000}; do
  curl -k -X POST https://localhost:8443/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{
      "email": "user@example.com",
      "password": "stringst"
    }'
done
