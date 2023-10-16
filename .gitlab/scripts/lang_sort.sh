#!/bin/bash

# Get the script's own path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Log file path
LOGFILE="${SCRIPT_DIR}/lang_sort_log.txt"

# Redirect stdout and stderr to the logfile
exec > "${LOGFILE}" 2>&1

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found, please install jq first."
    exit
fi

# Check for directory argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/translations"
    exit
fi

# Directory containing the JSON files to sort
DIR="$1"

# Check if en_EN.json exists in the directory
if [[ ! -f "${DIR}/en_EN.json" ]]; then
    echo "The file en_EN.json does not exist in ${DIR}.Ensure you have the right directory, Exiting."
    exit
fi

# Ensure locale is set to C for predictable sorting
export LC_ALL=C
export LC_COLLATE=C

# Sort keys of the en_EN.json file with 4-space indentation and overwrite it
jq -S --indent 4 '.' "${DIR}/en_EN.json" > "${DIR}/en_EN.json.tmp" && mv "${DIR}/en_EN.json.tmp" "${DIR}/en_EN.json"

# Function to recursively find all keys in a JSON object
function get_keys {
    jq -r 'paths(scalars) | join("/")' "$1"
}

# Get keys and subkeys from en_EN.json
ref_keys=$(mktemp)
get_keys "${DIR}/en_EN.json" | sort > "${ref_keys}"

# Iterate over each .json file in the directory
for file in "${DIR}"/*.json; do
    # Check if file is a regular file and not en_EN.json
    if [[ -f "${file}" && "${file}" != "${DIR}/en_EN.json" ]]; then

        # Get keys and subkeys from the current file
        current_keys=$(mktemp)
        get_keys "${file}" | sort > "${current_keys}"

        # Display keys present in en_EN.json but not in the current file
        missing_keys=$(comm -23 "${ref_keys}" "${current_keys}")
        if [[ -n "${missing_keys}" ]]; then
            echo -e "\nKeys/subkeys present in en_EN.json but missing in $(basename "${file}"): "
            echo "${missing_keys}"
        fi

        # Sort keys of the JSON file and overwrite the original file
        jq -S --indent 4 '.' "${file}" > "${file}.tmp" && mv "${file}.tmp" "${file}"

        # Remove the temporary file
        rm -f "${current_keys}"
    fi
done

# Remove the temporary file
rm -f "${ref_keys}"

echo -e "\n\nComparison and sorting complete!"
