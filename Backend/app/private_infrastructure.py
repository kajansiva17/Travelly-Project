"""Private filesystem primitives. Provision paths offline; never silently create them in requests."""
import os
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from .errors import ApiError


def unavailable():
    return ApiError(503, 'REVIEW_DEPENDENCY_UNAVAILABLE', 'The review service is temporarily unavailable.')


def private_root(value):
    if not value:
        raise unavailable()
    root = Path(value).absolute()
    repository = Path(__file__).resolve().parents[2]
    if root.is_relative_to(repository) or repository.is_relative_to(root):
        raise unavailable()
    # Reject junctions/reparse points at every component, including ancestors.
    for p in [root, *root.parents]:
        info = p.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise unavailable()
    if not root.is_dir():
        raise unavailable()
    return root


@contextmanager
def file_lock(path, timeout=5):
    """OS lock shared by independent workers; a crash releases it automatically."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    if os.fstat(fd).st_size == 0:
        os.write(fd, b'0')
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise unavailable() from None
                time.sleep(.025)
        yield
    finally:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def sync_directory(root):
    # Windows final placement uses MoveFileExW(MOVEFILE_WRITE_THROUGH).
    if os.name != 'nt':
        fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def durable_move(source, destination):
    if destination.exists():
        raise unavailable()
    if os.name == 'nt':
        import ctypes
        if not ctypes.windll.kernel32.MoveFileExW(str(source), str(destination), 0x8):
            raise OSError('Private placement failed')
    else:
        os.rename(source, destination)
        sync_directory(destination.parent)
