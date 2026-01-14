*Most of this README was automatically generated using Google Gemini Pro 3 and was manually reviewed for correctness by Constantin Schreyer*

# Malware Scanner

This component is a custom Python wrapper for **ClamAV**. It provides a streamlined interface for updating virus definitions and recursively scanning specific directories (primarily targeted at mounting external media like USB sticks).


## Setup
Copy the scanner.py file into the VM (opt/scanner/scanner.py)


## Design Rationale
While ClamAV offers a multi-threaded daemon (`clamd`), this project utilizes a direct wrapper around `clamscan` and `freshclam`. This approach was chosen for:
* **Simplicity:** No need to manage a background service state.
* **Customizability:** Direct control over subprocess execution and output parsing.
* **Workflow Fit:** Optimized for on-demand scanning of new media rather than continuous file system monitoring.

# Execution Flow
1. **Database Update**: Runs `freshclam` to pull the latest virus signatures. If the update fails, the script logs a warning but proceeds with the scan.
2. **Scan**: Executes `clamscan` recursively (`-r`) with verbose output (`-v`) on the target directory.
3. **Analysis**: The wrapper parses `stdout` for infection status and handles logging.

# Exit Codes
This component uses specific exit codes to communicate with the VM daemon or calling process:
* `0` → **Clean**: No malware found.
* `1` → **Infected**: Malware was detected in the target directory.
* `2` → **Error**: Invalid arguments, missing directory, or scanner failure.

# Logging
Logs are written to `stdout` and the `LOG_FILE` simultaneously with timestamps.
* **Info**: Start/stop events, scan progress, clean results.
* **Warning**: Malware detection, freshclam failures.
* **Error**: Critical failures (missing directories, argument errors).