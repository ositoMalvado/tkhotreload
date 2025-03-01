import os
import sys
import json
import tempfile
import fnmatch
import subprocess
import tkinter as tk


class TkinterHotReload(tk.Tk):
    """A hot reload implementation for Tkinter applications.

    This class provides functionality to automatically reload a Tkinter application
    when changes are detected in the source files. It preserves the window state
    (position, size, title, etc.) between reloads, providing a seamless development
    experience.

    Attributes:
        RELOADING_CODE (int): Exit code used to signal that the application should reload.
    """

    def properties(self, **kwargs):
        """Set multiple window properties at once.

        Args:
            title (str): Window title text.
            always_on_top (bool): Keep window on top of others.
            resizable (tuple): (width_resizable, height_resizable).
            alpha (float): Window transparency (0.0-1.0).
            min_size (tuple): Minimum (width, height) in pixels.
            max_size (tuple): Maximum (width, height) in pixels.
            fullscreen (bool): Enable fullscreen mode.
            icon (str): Path to .ico file for window icon.
            debug (bool): Enable debug prints when True, disable when False.

        Example:
            root.properties(
                title="My App",
                always_on_top=True,
                resizable=(False, False)
            )
        """
        for key, value in kwargs.items():
            if key == "title":
                self._title = value
                self.wm_title(value)
            elif key == "always_on_top":
                self._always_on_top = value
                self.attributes("-topmost", value)
            elif key == "resizable":
                self._resizable_x, self._resizable_y = value
                self.resizable(self._resizable_x, self._resizable_y)
            elif key == "alpha":
                self._alpha = value
                self.attributes("-alpha", value)
            elif key == "min_size":
                self._min_width, self._min_height = value
                if self._min_width > 0 and self._min_height > 0:
                    self.minsize(self._min_width, self._min_height)
            elif key == "max_size":
                self._max_width, self._max_height = value
                if self._max_width > 0 and self._max_height > 0:
                    self.maxsize(self._max_width, self._max_height)
            elif key == "fullscreen":
                self._fullscreen = value
                self.attributes("-fullscreen", value)
            elif key == "icon":
                self._icon_path = value
                try:
                    self.iconbitmap(self._icon_path)
                except Exception as e:
                    if getattr(self, "_debug", False):
                        if self._debug:
                            print(f"Error setting icon: {e}")
            elif key == "debug":
                self._debug = value
        return self

    RELOADING_CODE = 3

    def __init__(self, app_factory, target, watch_dir=None, exclude=None, debug=False):
        """Initialize the TkinterHotReload instance.

        Args:
            app_factory (callable): A function that creates and returns a Tkinter root window.
            target (callable): The main function of the application that takes the root window as an argument.
            watch_dir (str, optional): Directory to watch for file changes. Defaults to the script's directory.
            exclude (list, optional): List of patterns to exclude from file watching. Defaults to common patterns.
            debug (bool, optional): Enable debug prints when True, disable when False. Defaults to False.
        """
        self.app_factory = app_factory
        self.target = target
        self.watch_dir = watch_dir or os.path.dirname(os.path.abspath(sys.argv[0]))
        self.exclude = exclude or ["__pycache__", ".git", "venv", ".idea", "*.pyc"]
        self.state_file = os.path.join(
            tempfile.gettempdir(), "tkinter_hot_reload_state.json"
        )
        self._debug = debug
        self.tracked_files = self._get_all_files()
        self.last_mtime = {f: os.path.getmtime(f) for f in self.tracked_files}

    def _get_all_files(self):
        """Get all files in the watched directory that are not excluded.

        Returns:
            list: A list of file paths to be monitored for changes.
        """
        files = []
        for root, dirs, filenames in os.walk(self.watch_dir):
            dirs[:] = [d for d in dirs if not self._is_excluded(d)]
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if not self._is_excluded(filepath):
                    files.append(filepath)
        return files

    def _is_excluded(self, path):
        """Check if a path should be excluded from file watching.

        Args:
            path (str): The file or directory path to check.

        Returns:
            bool: True if the path matches any exclusion pattern, False otherwise.
        """
        return any(fnmatch.fnmatch(path, pattern) for pattern in self.exclude)

    def _save_window_state(self, root):
        """Save the current state of the Tkinter window.

        This method captures various window properties like position, size, title,
        and other attributes, and saves them to a temporary file for restoration
        after reload.

        Args:
            root (tk.Tk): The Tkinter root window.
        """
        try:
            state = {
                "geometry": root.geometry(),
                "is_maximized": root.state() == "zoomed",
                "is_withdrawn": root.state() == "withdrawn",
                "title": getattr(root, "_title", root.title),
                "always_on_top": getattr(root, "_always_on_top", False),
                "resizable": (
                    getattr(root, "_resizable_x", True),
                    getattr(root, "_resizable_y", True),
                ),
                "alpha": getattr(root, "_alpha", 1.0),
                "min_size": (
                    getattr(root, "_min_width", 0),
                    getattr(root, "_min_height", 0),
                ),
                "max_size": (
                    getattr(root, "_max_width", 0),
                    getattr(root, "_max_height", 0),
                ),
                "fullscreen": getattr(root, "_fullscreen", False),
                "icon": getattr(root, "_icon_path", None),
            }
            if self._debug:
                print(
                    f"[DEBUG] Saving window state with title: {root.title}, _title: {getattr(root, '_title', 'N/A')}"
                )
            with open(self.state_file, "w") as f:
                json.dump(state, f)
            if self._debug:
                print(f"[DEBUG] State saved to file: {self.state_file}")
        except Exception as e:
            print(f"Error saving state: {e}")

    def _load_window_state(self, root):
        """Load and apply the saved window state to the Tkinter window.

        This method reads the saved window properties from a temporary file and
        applies them to the newly created window after a reload.

        Args:
            root (tk.Tk): The Tkinter root window.
        """
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                if self._debug:
                    print(f"[DEBUG] Loaded state from file: {self.state_file}")
                    print(
                        f"[DEBUG] Loaded title from state: {state.get('title', 'N/A')}"
                    )
                    print(
                        f"[DEBUG] Current root title before restore: {root.title}, _title: {getattr(root, '_title', 'N/A')}"
                    )

                root.withdraw()
                root.geometry(state.get("geometry", ""))
                if state.get("is_maximized"):
                    root.state("zoomed")

                # Restore window properties
                if "title" in state:
                    if self._debug:
                        print(f"[DEBUG] Setting title from state: {state['title']}")
                    root._title = state["title"]
                    root.wm_title(state["title"])
                if "always_on_top" in state:
                    root._always_on_top = state["always_on_top"]
                    root.attributes("-topmost", state["always_on_top"])
                if "resizable" in state:
                    root._resizable_x, root._resizable_y = state["resizable"]
                    root.resizable(root._resizable_x, root._resizable_y)
                if "alpha" in state:
                    root._alpha = state["alpha"]
                    root.attributes("-alpha", root._alpha)
                if "min_size" in state:
                    root._min_width, root._min_height = state["min_size"]
                    if root._min_width > 0 and root._min_height > 0:
                        root.minsize(root._min_width, root._min_height)
                if "max_size" in state:
                    root._max_width, root._max_height = state["max_size"]
                    if root._max_width > 0 and root._max_height > 0:
                        root.maxsize(root._max_width, root._max_height)
                if "fullscreen" in state:
                    root._fullscreen = state["fullscreen"]
                    root.attributes("-fullscreen", root._fullscreen)
                if "icon" in state and state["icon"]:
                    root._icon_path = state["icon"]
                    try:
                        root.iconbitmap(root._icon_path)
                    except Exception as e:
                        if self._debug:
                            print(f"Error setting icon: {e}")

                if self._debug:
                    print(
                        f"[DEBUG] Root title after restore: {root.title}, _title: {getattr(root, '_title', 'N/A')}"
                    )

                if not state.get("is_withdrawn", False):
                    root.deiconify()
            except Exception as e:
                if self._debug:
                    print(f"Error loading state: {e}")

    def trigger_reload(self, root):
        """Trigger a reload of the application.

        This method saves the current window state and exits the application
        with a special code that signals it should be restarted.

        Args:
            root (tk.Tk): The Tkinter root window.
        """
        if self._debug:
            print(
                f"[DEBUG] Triggering reload with title: {root.title}, _title: {getattr(root, '_title', 'N/A')}"
            )
        self._save_window_state(root)
        if self._debug:
            print("Reloading application...")
        sys.exit(self.RELOADING_CODE)

    def start_process(self):
        """Start the application process and handle reloads.

        This method starts the application and restarts it when a reload is triggered.
        It continues this cycle until the application exits with a code other than
        the reload code.

        Returns:
            int: The final exit code of the application.
        """
        while True:
            if self._debug:
                print("Starting application...")
            args = [sys.executable] + sys.argv
            env = os.environ.copy()
            env["TKINTER_MAIN"] = "true"
            exit_code = subprocess.call(args, env=env)
            if exit_code != self.RELOADING_CODE:
                return exit_code

    def run_with_reloader(self):
        """Run the application with hot reload functionality.

        This method either starts the monitoring process or runs the application
        with file change detection, depending on the environment.
        """
        if os.environ.get("TKINTER_MAIN") == "true":
            root = self.app_factory()
            if self._debug:
                print(
                    f"[DEBUG] After app_factory - root.title: {root.title}, _title: {getattr(root, '_title', 'N/A')}"
                )

            self._load_window_state(root)
            # Apply the properties before calling the target function
            if hasattr(root, "title") and hasattr(root, "_title"):
                if self._debug:
                    print(f"[DEBUG] Applying title with wm_title: {root._title}")
                root.wm_title(root._title)
            if hasattr(root, "always_on_top") and hasattr(root, "_always_on_top"):
                root.attributes("-topmost", root._always_on_top)
            if (
                hasattr(root, "resizable_x")
                and hasattr(root, "_resizable_x")
                and hasattr(root, "resizable_y")
                and hasattr(root, "_resizable_y")
            ):
                root.resizable(root._resizable_x, root._resizable_y)
            if hasattr(root, "alpha") and hasattr(root, "_alpha"):
                root.attributes("-alpha", root._alpha)
            if (
                hasattr(root, "min_width")
                and hasattr(root, "_min_width")
                and hasattr(root, "min_height")
                and hasattr(root, "_min_height")
            ):
                if root._min_width > 0 and root._min_height > 0:
                    root.minsize(root._min_width, root._min_height)
            if (
                hasattr(root, "max_width")
                and hasattr(root, "_max_width")
                and hasattr(root, "max_height")
                and hasattr(root, "_max_height")
            ):
                if root._max_width > 0 and root._max_height > 0:
                    root.maxsize(root._max_width, root._max_height)
            if hasattr(root, "fullscreen") and hasattr(root, "_fullscreen"):
                root.attributes("-fullscreen", root._fullscreen)
            if (
                hasattr(root, "icon_path")
                and hasattr(root, "_icon_path")
                and root._icon_path
            ):
                try:
                    root.iconbitmap(root._icon_path)
                except Exception as e:
                    if self._debug:
                        print(f"Error setting icon: {e}")

            if self._debug:
                print(
                    f"[DEBUG] Before target function - root.title: {root.title}, _title: {getattr(root, '_title', 'N/A')}"
                )
            self.target(root)
            if self._debug:
                print(
                    f"[DEBUG] After target function - root.title: {root.title}, _title: {getattr(root, '_title', 'N/A')}"
                )

            def check_changes():
                try:
                    for filepath in self.tracked_files:
                        if not os.path.exists(filepath):
                            continue
                        current_mtime = os.path.getmtime(filepath)
                        if current_mtime > self.last_mtime.get(filepath, 0):
                            if self._debug:
                                print(f"Change detected: {filepath}")
                            self.trigger_reload(root)
                    self.tracked_files = self._get_all_files()
                    self.last_mtime = {
                        f: os.path.getmtime(f) for f in self.tracked_files
                    }
                except Exception as e:
                    if self._debug:
                        print(f"Error: {e}")
                root.after(root.reload_interval, check_changes)

            check_changes()
            root.mainloop()
        else:
            sys.exit(self.start_process())

    @staticmethod
    def app(
        target,
        watch_dir=None,
        exclude=None,
        always_on_top=False,
        title="Tkinter Hot Reload",
        debug_mode=False,
        reload_interval=1000,
        resizable=(True, True),
        alpha=1.0,
        min_size=(0, 0),
        max_size=(0, 0),
        fullscreen=False,
        icon_path=None,
    ):
        """Create and run a Tkinter application with hot reload functionality.

        This is the main entry point for using the hot reload functionality. It sets up
        the application with the specified properties and monitors for file changes.

        Args:
            target (callable): The main function of the application that takes the root window as an argument.
            watch_dir (str, optional): Directory to watch for file changes. Defaults to the script's directory.
            exclude (list, optional): List of patterns to exclude from file watching. Defaults to common patterns.
            always_on_top (bool, optional): Whether the window should stay on top of other windows. Defaults to False.
            title (str, optional): The window title. Defaults to "Tkinter Hot Reload".
            debug_mode (bool, optional): Whether to enable debug mode with additional logging. Defaults to False.
            reload_interval (int, optional): Interval in milliseconds to check for file changes. Defaults to 1000.
            resizable (tuple, optional): Whether the window is resizable (width, height). Defaults to (True, True).
            alpha (float, optional): Window transparency level (0.0 to 1.0). Defaults to 1.0.
            min_size (tuple, optional): Minimum window size (width, height). Defaults to (0, 0).
            max_size (tuple, optional): Maximum window size (width, height). Defaults to (0, 0).
            fullscreen (bool, optional): Whether to start in fullscreen mode. Defaults to False.
            icon_path (str, optional): Path to the window icon file. Defaults to None.

        Returns:
            CustomTk: The root window instance.

        Example:
            root.properties(
                title="My App",
                always_on_top=True,
                resizable=(False, False),
                alpha=0.95,
                min_size=(800, 600),
                icon="icon.ico"
            )
        """

        def app_factory():
            root = tk.Tk()

            # Define property setters and getters
            def get_title(obj):
                """Get the window title.

                Returns:
                    str: The current window title.
                """
                value = getattr(obj, "_title", title)
                print(f"[DEBUG] get_title called, returning: {value}")
                return value

            def set_title(obj, value):
                """Set the window title.

                Args:
                    value (str): The new window title.
                """
                print(f"[DEBUG] set_title called with value: {value}")
                obj._title = value
                obj.wm_title(value)
                # Force update the window title
                obj.update()

            def get_always_on_top(obj):
                """Get the always-on-top state of the window.

                Returns:
                    bool: True if the window is set to always be on top, False otherwise.
                """
                return getattr(obj, "_always_on_top", always_on_top)

            def set_always_on_top(obj, value):
                """Set the always-on-top state of the window.

                Args:
                    value (bool): True to make the window always on top, False otherwise.
                """
                obj._always_on_top = value
                obj.attributes("-topmost", value)

            def get_resizable_x(obj):
                """Get the horizontal resizability of the window.

                Returns:
                    bool: True if the window is horizontally resizable, False otherwise.
                """
                return getattr(obj, "_resizable_x", resizable[0])

            def set_resizable_x(obj, value):
                """Set the horizontal resizability of the window.

                Args:
                    value (bool): True to make the window horizontally resizable, False otherwise.
                """
                obj._resizable_x = value
                obj.resizable(value, obj._resizable_y)

            def get_resizable_y(obj):
                """Get the vertical resizability of the window.

                Returns:
                    bool: True if the window is vertically resizable, False otherwise.
                """
                return getattr(obj, "_resizable_y", resizable[1])

            def set_resizable_y(obj, value):
                """Set the vertical resizability of the window.

                Args:
                    value (bool): True to make the window vertically resizable, False otherwise.
                """
                obj._resizable_y = value
                obj.resizable(obj._resizable_x, value)

            def get_alpha(obj):
                """Get the window transparency level.

                Returns:
                    float: The current transparency level (0.0 to 1.0).
                """
                return getattr(obj, "_alpha", alpha)

            def set_alpha(obj, value):
                """Set the window transparency level.

                Args:
                    value (float): The transparency level between 0.0 (fully transparent) and 1.0 (fully opaque).
                """
                if 0.0 <= value <= 1.0:
                    obj._alpha = value
                    obj.attributes("-alpha", value)

            def get_min_width(obj):
                """Get the minimum window width.

                Returns:
                    int: The minimum allowed window width in pixels.
                """
                return getattr(obj, "_min_width", min_size[0])

            def set_min_width(obj, value):
                """Set the minimum window width.

                Args:
                    value (int): The minimum allowed window width in pixels.
                """
                obj._min_width = value
                if value > 0 and obj._min_height > 0:
                    obj.minsize(value, obj._min_height)

            def get_min_height(obj):
                """Get the minimum window height.

                Returns:
                    int: The minimum allowed window height in pixels.
                """
                return getattr(obj, "_min_height", min_size[1])

            def set_min_height(obj, value):
                """Set the minimum window height.

                Args:
                    value (int): The minimum allowed window height in pixels.
                """
                obj._min_height = value
                if obj._min_width > 0 and value > 0:
                    obj.minsize(obj._min_width, value)

            def get_max_width(obj):
                """Get the maximum window width.

                Returns:
                    int: The maximum allowed window width in pixels.
                """
                return getattr(obj, "_max_width", max_size[0])

            def set_max_width(obj, value):
                """Set the maximum window width.

                Args:
                    value (int): The maximum allowed window width in pixels.
                """
                obj._max_width = value
                if value > 0 and obj._max_height > 0:
                    obj.maxsize(value, obj._max_height)

            def get_max_height(obj):
                """Get the maximum window height.

                Returns:
                    int: The maximum allowed window height in pixels.
                """
                return getattr(obj, "_max_height", max_size[1])

            def set_max_height(obj, value):
                """Set the maximum window height.

                Args:
                    value (int): The maximum allowed window height in pixels.
                """
                obj._max_height = value
                if obj._max_width > 0 and value > 0:
                    obj.maxsize(obj._max_width, value)

            def get_fullscreen(obj):
                """Get the fullscreen state of the window.

                Returns:
                    bool: True if the window is in fullscreen mode, False otherwise.
                """
                return getattr(obj, "_fullscreen", fullscreen)

            def set_fullscreen(obj, value):
                """Set the fullscreen state of the window.

                Args:
                    value (bool): True to enable fullscreen mode, False to disable.
                """
                obj._fullscreen = value
                obj.attributes("-fullscreen", value)

            def get_icon_path(obj):
                """Get the path to the window icon file.

                Returns:
                    str: The path to the current window icon file, or None if not set.
                """
                return getattr(obj, "_icon_path", icon_path)

            def set_icon_path(obj, value):
                """Set the window icon using the specified file path.

                Args:
                    value (str): The path to the icon file (.ico format for Windows).
                """
                obj._icon_path = value
                if value:
                    try:
                        obj.iconbitmap(value)
                    except Exception as e:
                        print(f"Error   setting icon: {e}")

            # Add properties using property decorator
            root.title = property(get_title, set_title)
            root.always_on_top = property(get_always_on_top, set_always_on_top)
            root.resizable_x = property(get_resizable_x, set_resizable_x)
            root.resizable_y = property(get_resizable_y, set_resizable_y)
            root.alpha = property(get_alpha, set_alpha)
            root.min_width = property(get_min_width, set_min_width)
            root.min_height = property(get_min_height, set_min_height)
            root.max_width = property(get_max_width, set_max_width)
            root.max_height = property(get_max_height, set_max_height)
            root.fullscreen = property(get_fullscreen, set_fullscreen)
            root.icon_path = property(get_icon_path, set_icon_path)

            # Define properties method as a bound method
            def properties_method(**kwargs):
                """Set multiple window properties at once.

                Args:
                    **kwargs: Keyword arguments for window properties. Supported options:
                        title (str): Window title text.
                        always_on_top (bool): Keep window on top of others (True/False).
                        resizable (tuple): (width_resizable, height_resizable) as booleans.
                        alpha (float): Window transparency (0.0 transparent - 1.0 opaque).
                        min_size (tuple): Minimum (width, height) in pixels.
                        max_size (tuple): Maximum (width, height) in pixels.
                        fullscreen (bool): Start in fullscreen mode (True/False).
                        icon (str): Path to .ico file for window icon.

                Returns:
                    tk.Tk: The root window instance.

                Example:
                    root.properties(
                        title="My App",
                        always_on_top=True,
                        resizable=(False, False),
                        alpha=0.95,
                        min_size=(800, 600),
                        icon="icon.ico"
                    )
                """
                for key, value in kwargs.items():
                    if key == "title":
                        root._title = value
                        root.wm_title(value)
                    elif key == "always_on_top":
                        root._always_on_top = value
                        root.attributes("-topmost", value)
                    elif key == "resizable":
                        if isinstance(value, tuple) and len(value) == 2:
                            root._resizable_x, root._resizable_y = value
                            root.resizable(value[0], value[1])
                    elif key == "alpha":
                        if 0.0 <= value <= 1.0:
                            root._alpha = value
                            root.attributes("-alpha", value)
                    elif key == "min_size":
                        if isinstance(value, tuple) and len(value) == 2:
                            root._min_width, root._min_height = value
                            if value[0] > 0 and value[1] > 0:
                                root.minsize(value[0], value[1])
                    elif key == "max_size":
                        if isinstance(value, tuple) and len(value) == 2:
                            root._max_width, root._max_height = value
                            if value[0] > 0 and value[1] > 0:
                                root.maxsize(value[0], value[1])
                    elif key == "fullscreen":
                        root._fullscreen = value
                        root.attributes("-fullscreen", value)
                    elif key == "icon":
                        root._icon_path = value
                        if value:
                            try:
                                root.iconbitmap(value)
                            except Exception as e:
                                print(f"Error setting icon: {e}")
                return root

            root.properties = properties_method

            # Set initial values
            root.title = title
            root.always_on_top = always_on_top
            root._resizable_x, root._resizable_y = resizable
            root.resizable(resizable[0], resizable[1])
            root._alpha = alpha

            # Add other properties
            root.debug_mode = debug_mode
            root.reload_interval = reload_interval

            return root

        print("Starting app...")
        hot_reload = TkinterHotReload(
            app_factory=app_factory,
            target=target,
            watch_dir=watch_dir,
            exclude=exclude,
        )
        hot_reload.run_with_reloader()
