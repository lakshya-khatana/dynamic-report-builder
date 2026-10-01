"""Spec §5.3: 'Standard UTF-8 encoded text stream', chunked."""

import csv
import io
from collections.abc import Iterator


def export_to_csv(columns: list[str], row_iterator: Iterator[tuple], output_path: str) -> str:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in row_iterator:
            writer.writerow(row)
    return output_path


def stream_csv_response(columns: list[str], row_iterator: Iterator[tuple]) -> Iterator[str]:
    """
    For a FastAPI StreamingResponse — yields text chunks instead of writing
    to disk, so an export can go straight to the HTTP response body.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)

    for row in row_iterator:
        writer.writerow(row)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
