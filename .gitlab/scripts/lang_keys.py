import json
import os


def get_missing_keys_and_values(obj1, obj2, path=None):
    if path is None:
        path = []

    missing_keys_and_values = {}

    if isinstance(obj1, dict) and isinstance(obj2, dict):
        for key in obj1:
            if key not in obj2:
                missing_keys_and_values[key] = obj1[key]
            elif isinstance(obj1[key], (dict, list)) and isinstance(
                obj2[key], (dict, list)
            ):
                sub_missing = get_missing_keys_and_values(
                    obj1[key], obj2[key], path + [key]
                )
                if sub_missing:
                    missing_keys_and_values[key] = sub_missing

    return missing_keys_and_values


def main():
    dir_path = "../../app/translations"  # Get the current working directory

    en_en_path = os.path.join(dir_path, "en_EN.json")

    if not os.path.isfile(en_en_path):
        print(
            f"The file en_EN.json does not exist in {dir_path}. "
            "Ensure you have the right directory, Exiting."
        )
        return

    with open(en_en_path, "r", encoding="utf-8") as en_en_file:
        en_en_data = json.load(en_en_file)

    result = {}  # JSON object to store missing keys and values

    for root, _, files in os.walk(dir_path):
        for file in files:
            if file != "en_EN.json" and file.endswith(".json"):
                file_path = os.path.join(root, file)

                with open(file_path, "r", encoding="utf-8") as current_file:
                    current_data = json.load(current_file)

                missing_keys_and_values = get_missing_keys_and_values(
                    en_en_data, current_data
                )
                if missing_keys_and_values:
                    result[file] = missing_keys_and_values

    # Write the JSON object to lang_sort.txt
    with open("lang_sort.txt", "w", encoding="utf-8") as output_file:
        json.dump(result, output_file, indent=4)


if __name__ == "__main__":
    main()
