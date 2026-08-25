"""Basic desktop UI for running classify.py and check.py.

Two buttons run the scripts as subprocesses and show their stdout/stderr
in a scrollable text panel below.
"""

import subprocess
import sys
import tkinter as tk
from tkinter import scrolledtext

SCRIPTS = {
    "Run Classifier": "classify.py",
    "Run Check": "check.py",
}


def run_script(script_name, output):
    output.configure(state="normal")
    output.delete("1.0", tk.END)
    output.insert(tk.END, f"$ python3 {script_name}\n\n")
    output.update()

    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=True,
        text=True,
    )
    output.insert(tk.END, result.stdout)
    if result.stderr:
        output.insert(tk.END, "\n" + result.stderr)
    output.configure(state="disabled")


def main():
    root = tk.Tk()
    root.title("CARPARC classifier")
    root.geometry("800x600")

    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=10)

    output = scrolledtext.ScrolledText(root, wrap=tk.WORD, state="disabled")
    output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    for label, script_name in SCRIPTS.items():
        tk.Button(
            button_frame,
            text=label,
            command=lambda s=script_name: run_script(s, output),
        ).pack(side=tk.LEFT, padx=(0, 8))

    root.mainloop()


if __name__ == "__main__":
    main()
