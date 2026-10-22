
#!/usr/bin/env bash
set -euo pipefail
mkdir -p ../frontend/public/wasm

em++ -O2 -std=c++20 -Iinclude src/airportops.cpp \
 -s MODULARIZE=1 \
 -s EXPORT_NAME=AirportOpsModule \
 -s ENVIRONMENT=web,worker \
 -s ALLOW_MEMORY_GROWTH=1 \
 -s EXPORTED_FUNCTIONS='["_ao_reset","_ao_step","_ao_time","_ao_flight_count","_ao_flight","_ao_stat","_ao_vehicle_count","_ao_vehicle","_ao_path"]' \
 -s EXPORTED_RUNTIME_METHODS='["ccall"]' \
 -o ../frontend/public/wasm/airportops.js
