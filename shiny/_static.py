import json
import os
import shutil
import sys
from typing import Callable, List, Optional

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


# This is the same as the FileContent type in TypeScript.
class FileContent(TypedDict):
    name: str
    content: str


def deploy_static(
    appdir: str,
    destdir: str,
    *,
    overwrite: bool = False,
    subdir: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """
    Statically deploy a Shiny app.
    """

    def verbose_print(*args: object) -> None:
        if verbose:
            print(*args)

    if subdir is None:
        subdir = ""
    if os.path.isabs(subdir):
        raise ValueError("subdir must be a relative path")

    shinylive_source_dir = os.path.join(os.path.dirname(__file__), "js")
    verbose_print(f"Copying {shinylive_source_dir} to {destdir}")
    os.makedirs(destdir, exist_ok=True)
    shutil.copytree(
        shinylive_source_dir,
        destdir,
        copy_function=_copy_fn(overwrite, verbose_print=verbose_print),
        dirs_exist_ok=True,
    )

    app_files: List[FileContent] = []
    # Recursively iterate over files in app directory, and collect the files into
    # app_files data structure.
    exclude_names = {"__pycache__"}
    for root, dirs, files in os.walk(appdir, topdown=True):
        dirs[:] = set(dirs) - exclude_names
        rel_dir = os.path.relpath(root, appdir)
        files = [f for f in files if not f.startswith(".")]
        files.sort()

        # Move app.py to first in list.
        if "app.py" in files:
            app_py_idx = files.index("app.py")
            files.insert(0, files.pop(app_py_idx))

        # Add the file to the app_files list.
        for filename in files:
            if rel_dir == ".":
                output_filename = filename
            else:
                output_filename = os.path.join(rel_dir, filename)

            file_content = (
                open(os.path.join(root, filename), "rb").read().decode("utf-8")
            )

            app_files.append(
                {
                    "name": output_filename,
                    "content": file_content,
                }
            )

    # Write the index.html, editor/index.html, and app.json in the destdir.
    html_source_dir = os.path.join(os.path.dirname(__file__), "html")
    app_destdir = os.path.join(destdir, subdir)

    # For a subdir like a/b/c, this will be ../../../
    subdir_inverse = "/".join([".."] * _path_length(subdir))
    if subdir_inverse != "":
        subdir_inverse += "/"

    os.makedirs(app_destdir, exist_ok=True)
    _copy_file_and_substitute(
        src=os.path.join(html_source_dir, "index.html"),
        dest=os.path.join(app_destdir, "index.html"),
        search_str="{{REL_PATH}}",
        replace_str=subdir_inverse,
    )

    os.makedirs(os.path.join(app_destdir, "editor"), exist_ok=True)
    _copy_file_and_substitute(
        src=os.path.join(html_source_dir, "editor", "index.html"),
        dest=os.path.join(app_destdir, "editor", "index.html"),
        search_str="{{REL_PATH}}",
        replace_str=subdir_inverse,
    )

    app_json_output_file = os.path.join(app_destdir, "app.json")

    verbose_print("Writing to " + app_json_output_file)
    json.dump(app_files, open(app_json_output_file, "w"))


def _copy_fn(
    overwrite: bool, verbose_print: Callable[..., None] = lambda x: None
) -> Callable[..., None]:
    """Returns a function that can be used as a copy_function for shutil.copytree.

    If overwrite is True, the copy function will overwrite files that already exist.
    If overwrite is False, the copy function will not overwrite files that already exist.
    """

    def mycopy(src: str, dst: str, **kwargs: object) -> None:
        if os.path.exists(dst):
            if overwrite:
                verbose_print(f"Overwriting {dst}")
                os.remove(dst)
            else:
                verbose_print(f"Skipping {dst}")
                return

        shutil.copy2(src, dst, **kwargs)

    return mycopy


def _path_length(path: str) -> int:
    """Returns the number of elements in a path.

    For example 'a' has length 1, 'a/b' has length 2, etc.
    """

    if os.path.isabs(path):
        raise ValueError("path must be a relative path")

    path = os.path.normpath(path)
    if path == ".":
        return 0

    # On Windows, replace backslashes with forward slashes.
    if os.name == "nt":
        path.replace("\\", "/")

    return len(path.split("/"))


def _copy_file_and_substitute(
    src: str, dest: str, search_str: str, replace_str: str
) -> None:
    with open(src, "r") as fin:
        in_content = fin.read()
        in_content = in_content.replace(search_str, replace_str)
        with open(dest, "w") as fout:
            fout.write(in_content)