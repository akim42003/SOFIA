import json
import os
import subprocess

def save_file(action: str, path: str, content: str) -> str:
    try:
        # Expand the user directory in the given path.
        expanded_path = os.path.expanduser(path)

        # Check if the file already exists.
        if not os.path.isfile(expanded_path):
            return f"Error: File does not exist at {expanded_path}"

        # If it exists, update its content (overwriting the file).
        with open(expanded_path, 'w') as f:
            f.write(content)

        return f"File at {expanded_path} successfully updated."
    except Exception as e:
        return f"Error saving file: {e}"

def read_file(action: str, path: str):
    try:
        expanded_path = os.path.expanduser(path)
        # print(expanded_path)
        directory = os.path.dirname(expanded_path)
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok = True)

        with open(expanded_path, "r") as f:
            output = f.read()
        return output
    except Exception as e:
        return f"Error reading this file: {e}"


def execute_command(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        term_output = result.stdout.strip()
        nl_output = "command: " + command + " run successfully." + " This is the terminal output: " + term_output
        return nl_output
    except Exception as e:
        return f"Error executing command: {e}"

def reset_google_cred(remove_cred: bool) -> str:
    if remove_cred:
        try:
            result = subprocess.run("rm -rf token.json", shell = True, check = True,
                stdout = subprocess.PIPE, stderr = subprocess.PIPE, text = True)
            term_output = result.stdout.strip()
            nl_output = "google credentials reset. this is the terminal output: "+ term_output
            return nl_output
        except Exception as e:
            return f"Error executing command: {e}"
    else:
        return f"Error executing command: {e}"
