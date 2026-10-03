"""Disposable PDF parser: no file paths or persistent resume content."""
import asyncio
import sys


async def extract_pdf(content: bytes) -> str:
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.services.resume_parser",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(content), timeout=8)
        if process.returncode:
            raise ValueError("Invalid or unsupported PDF")
        return output.decode("utf-8")[:50000]
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


if __name__ == "__main__":
    import resource
    from io import BytesIO
    from pypdf import PdfReader
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    # Address-space limits are supported on Linux; macOS rejects some limits.
    if sys.platform == "linux":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    data = sys.stdin.buffer.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("Oversized PDF")
    reader = PdfReader(BytesIO(data))
    if reader.is_encrypted or len(reader.pages) > 10:
        raise ValueError("Unsupported PDF")
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "")[:50000 - len(text)] + "\n"
        if len(text) >= 50000:
            break
    sys.stdout.write(text[:50000])
