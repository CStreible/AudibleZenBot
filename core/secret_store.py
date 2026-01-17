"""
Secret store helpers using Windows DPAPI (CryptProtectData / CryptUnprotectData)
Falls back to plain storage if DPAPI not available.
"""
import base64
import sys

USE_DPAPI = sys.platform.startswith('win')

if USE_DPAPI:
    import ctypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', ctypes.c_uint32), ('pbData', ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    def _to_blob(data: bytes):
        blob = DATA_BLOB()
        blob.cbData = len(data)
        blob.pbData = ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte))
        return blob

    def protect_bytes(data: bytes) -> bytes:
        if not data:
            return b''
        in_blob = _to_blob(data)
        out_blob = DATA_BLOB()
        if crypt32.CryptProtectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)) == 0:
            raise OSError('CryptProtectData failed')
        try:
            cb = int(out_blob.cbData)
            ptr = out_blob.pbData
            buf = ctypes.string_at(ptr, cb)
            return buf
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def unprotect_bytes(data: bytes) -> bytes:
        if not data:
            return b''
        in_blob = _to_blob(data)
        out_blob = DATA_BLOB()
        if crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)) == 0:
            raise OSError('CryptUnprotectData failed')
        try:
            cb = int(out_blob.cbData)
            ptr = out_blob.pbData
            buf = ctypes.string_at(ptr, cb)
            return buf
        finally:
            kernel32.LocalFree(out_blob.pbData)

    def protect_string(plain: str) -> str:
        if plain is None:
            return ''
        b = plain.encode('utf-8')
        protected = protect_bytes(b)
        return 'ENC:' + base64.b64encode(protected).decode('ascii')

    def unprotect_string(enc: str) -> str:
        if not enc:
            return ''
        if not enc.startswith('ENC:'):
            return enc
        try:
            blob = base64.b64decode(enc[4:])
            plain = unprotect_bytes(blob)
            return plain.decode('utf-8')
        except Exception:
            return ''
else:
    # Non-Windows fallback: no encryption, but keep interface
    def protect_string(plain: str) -> str:
        return plain or ''

    def unprotect_string(enc: str) -> str:
        return enc or ''
