#!/bin/bash
# Activation script for ESS Testing

# Activate virtual environment
source /home/pi1/utilsenv/bin/activate

# Change to project directory
cd "/home/pi1/jig_one_v1.2"

# Run the Python application
python3 "/home/pi1/jig_one_v1.2/main.py" 

# Deactivate virtual environment when done
deactivate
