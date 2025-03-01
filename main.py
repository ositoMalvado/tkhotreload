import tkhotreload as tkhr
from tkinter import Label, Button


def main(root: tkhr.TkinterHotReload):
    # Use the new properties method to set multiple attributes at once
    root.properties(
        title="Tk Inter Reload 4",
        always_on_top=True,
        alpha=0.5,
        icon="icon.ico",
        debug=False,
    )
    Label(root, text="change this!").pack(pady=20)
    Button(root, text="Click me", command=lambda: print("Clicked!")).pack()


tkhr.app(target=main, watch_dir=".", exclude=["*.pyc", "__pycache__"])
