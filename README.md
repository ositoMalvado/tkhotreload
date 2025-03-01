# TkinterHotReload

A powerful hot reload utility for Tkinter applications that enables real-time code updates without restarting your application.

## Features

- 🔄 Live code reloading for Tkinter applications
- 🚀 Zero configuration required
- 🎯 Automatic detection of file changes
- 💻 Seamless development experience
- 🛠 Maintains application state during reloads

## Installation

Install TkinterHotReload using pip:

```bash
pip install tkhr --upgrade
```

## Quick Start

Here's a simple example of how to use TkinterHotReload:

```python
import tkhotreload as tkhr
from tkinter import Label, Button


def main(root: tkhr.TkinterHotReload):
    # Use the new properties method to set multiple attributes at once
    root.properties(
        title="Tk Inter Reload",
        always_on_top=True,
        alpha=0.5,
        icon="icon.ico",
        debug=False,
    )
    Label(root, text="Change this and save!").pack(pady=20)
    Button(root, text="Click me", command=lambda: print("Clicked!")).pack()


tkhr.app(target=main, watch_dir=".", exclude=["*.pyc", "__pycache__"])
```

## How It Works

TkinterHotReload monitors your Python files for changes. When you modify and save a file, it automatically:

1. Detects the changes in your code
2. Reloads the modified modules
3. Updates your Tkinter application while preserving its state

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please:

- Open an issue on GitHub
- Check existing issues for solutions
- Provide detailed information about your problem

## Acknowledgments

- Thanks to all contributors who have helped shape TkinterHotReload
- Inspired by hot reload functionality in modern web development

---

Made with ❤️ for the Python community