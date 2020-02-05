
import fnmatch
import os


def get_relative_path(root, path):
    """
    Return relative path from root path

    Returns None if not in same prefix
    """
    root_parts = root.split(os.sep)
    path_parts = path.split(os.sep)
    if path_parts[:len(root_parts)] == root_parts:
        return os.sep.join(path_parts[len(root_parts):])
    return None


def match_path_prefix(prefix, path):
    """
    Match path prefix for two paths with fnmatch applied to path components
    """
    if isinstance(prefix, str):
        prefix = prefix.split(os.sep)
    if isinstance(path, str):
        path = path.split(os.sep)

    for index, path_pattern in enumerate(prefix):
        if index > len(path) - 1:
            return False
        if not fnmatch.fnmatch(path[index], path_pattern):
            return False
    return True


def match_path_patterns(patterns, root, path):
    """
    Match specified path to filename patterns compared to root directory
    """
    filename = os.path.basename(path)
    relative_path = get_relative_path(root, path)

    for pattern in patterns:
        # Filename direct pattern match
        if relative_path == pattern or fnmatch.fnmatch(filename, pattern):
            return True

        parts = pattern.split(os.sep)
        if len(parts) == 1:
            continue

        if relative_path is not None and match_path_prefix(parts, relative_path):
            relative_pattern = parts[-1]
            if fnmatch.fnmatch(filename, relative_pattern):
                return True

    return False
