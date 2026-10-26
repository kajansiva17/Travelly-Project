"""Bounded isolated content validator; invoked in a disposable worker, never in a request thread."""
import os
import sys
import warnings


def limit_memory():
    if os.name != 'nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
    else:
        import ctypes
        from ctypes import wintypes
        class BASIC(ctypes.Structure):
            _fields_ = [('a', ctypes.c_longlong), ('b', ctypes.c_longlong), ('flags', wintypes.DWORD),
                        ('min', ctypes.c_size_t), ('max', ctypes.c_size_t), ('processes', wintypes.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ['r', 'w', 'o', 'rb', 'wb', 'ob']]
        class EXT(ctypes.Structure):
            _fields_ = [('basic', BASIC), ('io', IO), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        job = kernel.CreateJobObjectW(None, None)
        info = EXT(); info.basic.flags = 0x100; info.process_memory = 256 * 1024**2
        if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)) or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
            raise RuntimeError('Validator isolation unavailable')


def validate(path, mime):
    limit_memory()
    if mime == 'application/pdf':
        from pypdf import PdfReader
        with open(path, 'rb') as stream:
            if stream.read(5) != b'%PDF-':
                raise ValueError()
            stream.seek(0)
            pdf = PdfReader(stream, strict=True)
            if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 500:
                raise ValueError()
            for page in pdf.pages:
                page.get('/Resources')
    else:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = 20_000_000
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.format != {'image/png': 'PNG', 'image/jpeg': 'JPEG'}[mime] or image.width * image.height > 20_000_000:
                raise ValueError()
            image.verify()
        with Image.open(path) as image:
            image.load()


if __name__ == '__main__':
    try:
        validate(sys.argv[1], sys.argv[2])
    except (ImportError, RuntimeError):
        sys.exit(2)
    except Exception:
        sys.exit(1)
