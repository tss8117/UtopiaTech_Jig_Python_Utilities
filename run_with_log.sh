#!/bin/bash
# Run the utility and capture all output to a timestamped log file

source /home/pi1/utilsenv/bin/activate
cd "/home/pi1/jig_one_v1.2"

LOG_DIR="/home/pi1/jig_one_v1.2/crash_logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/run_$TIMESTAMP.log"

echo "=== Session started: $TIMESTAMP ===" | tee "$LOG_FILE"
echo "=== Log: $LOG_FILE ==="

# Run python and tee all stdout+stderr to the log file
python3 "/home/pi1/jig_one_v1.2/main.py" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo "" | tee -a "$LOG_FILE"
echo "=== Session ended: $(date +"%Y-%m-%d_%H-%M-%S") ===" | tee -a "$LOG_FILE"
echo "=== Exit code: $EXIT_CODE ===" | tee -a "$LOG_FILE"

deactivate
