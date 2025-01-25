import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

import openai


class ShellCommandCompletion(BaseModel):
    command_completion: str


# Configure logging
logging.basicConfig(
    filename=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "copilot.log"
    ),
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory to store temporary files, used to communicate with the terminal
TMP_FILES_DIR = os.path.join(SCRIPT_DIR, ".tmp")
tmp_files_dir_path = Path(TMP_FILES_DIR)

MIN_IDLE_TIME = 0.3
CHECK_INTERVAL = 0.1

openai.api_key = os.getenv("OPENAI_API_KEY")


def parse_file(file_path):
    logging.debug(f"Parsing file: {file_path}")
    with open(file_path, "r") as file:
        lines = file.readlines()

    current_prompt = lines[0].strip()
    current_directory = lines[1].strip()
    command_history = "".join(lines[3:18])
    ls_output = "".join(lines[18:])

    return {
        "current_prompt": current_prompt,
        "current_directory": current_directory,
        "command_history": command_history,
        "ls_output": ls_output,
    }


def serve_terminal_session(context_file_path, option_file_path):
    context_modification_time = os.path.getmtime(context_file_path)
    options_modification_time = os.path.getmtime(option_file_path)

    if (
        context_modification_time >= options_modification_time
        and (time.time() - context_modification_time) > MIN_IDLE_TIME
    ):
        logging.debug(
            f"Serving terminal session for context file: {context_file_path}"
        )
        context = parse_file(context_file_path)

        if not context:
            return

        prompt = f"""
        Current working directory: {context['current_directory']}
        Current command line prompt: {context['current_prompt']}
        Command line history: {context['command_history']}
        Output of 'ls' command: {context['ls_output']}
        """

        logging.debug(f"Sending prompt to OpenAI API: {prompt}")
        response = openai.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a command line copilot. Your goal is to provide accurate and context-aware command-line completions and suggestions based on the user's command history and current working directory. You should **ONLY** output the suggested command completion, without any additional comments or explanations, unless explicitly requested",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0,
            response_format=ShellCommandCompletion,
        )
        completion = response.choices[0].message.parsed.command_completion.strip()
        logging.debug(f"completion: {completion}")

        logging.debug(
            f"Writing completion to options file: {option_file_path}"
        )
        with open(option_file_path, "w") as file:
            file.write(completion)


def handle_tmp_files(directory):
    for f in tmp_files_dir_path.glob("*.context*"):
        context_file_path = os.path.join(directory, f.name)

        for option_f in tmp_files_dir_path.glob(
            f.name.replace(".context", ".options")[:-6] + "*"
        ):
            option_file_path = os.path.join(directory, option_f)

        try:
            serve_terminal_session(context_file_path, option_file_path)
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.error(
                f"Error processing file {context_file_path}: {str(e)}",
                exc_info=True,
            )


def watch_files():
    while True:
        handle_tmp_files(TMP_FILES_DIR)

        # Limit frequency of checking for changes
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    watch_files()
