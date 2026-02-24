#!/usr/bin/env bash
set -e

PORT=/dev/ttyUSB0
BAUD=3000000
OUTFILE=test.dat
EMIT_DEBUG=8
PWM_HZ=30000

# Capture duration in microseconds
CAPTURE_US=1000   # ~3 cycles @ 30 kHz

echo "[*] Configuring UART (${PORT})..."
sudo stty -F "${PORT}" ${BAUD} raw -echo -ixon -ixoff

echo "[*] Capturing high-rate data to ${OUTFILE}"
echo "[*] Capture duration: ${CAPTURE_US} µs"

# Ensure a fresh file
rm -f "${OUTFILE}"

# Start raw capture in background
cat "${PORT}" > "${OUTFILE}" &
CAT_PID=$!

# High-resolution sleep (very low overhead)
# perl select() is a single libc call under the hood
perl -e "select(undef, undef, undef, ${CAPTURE_US}/1e6);"

# Stop capture
kill "${CAT_PID}"
wait "${CAT_PID}" 2>/dev/null || true

echo "[*] Capture complete, plotting..."

python3 plot_highrate.py "${OUTFILE}" \
  --emit-debug ${EMIT_DEBUG} \
  --pwm-hz ${PWM_HZ}
