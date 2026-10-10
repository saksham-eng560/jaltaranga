"""Publish generated ML artifacts to the private Jaltaranga data bucket.

The default is a local dry run. Pass ``--apply`` to upload files; this script
never deletes existing S3 objects.
"""

from __future__ import annotations

import argparse
import mimetypes
import os
from pathlib import Path


ML_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ML_DIR / "out"
CONTENT_TYPES = {
    ".geojson": "application/geo+json",
    ".json": "application/json",
    ".tif": "image/tiff",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=os.environ.get("JT_DATA_BUCKET"))
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="upload the listed artifacts (without this flag, only print the upload plan)",
    )
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    if not out_dir.is_dir():
        parser.error(f"artifact directory does not exist: {out_dir}")

    files = sorted(path for path in out_dir.rglob("*") if path.is_file())
    if not files:
        parser.error(f"no artifacts found under {out_dir}")
    if args.apply and not args.bucket:
        parser.error("--bucket or JT_DATA_BUCKET is required with --apply")

    s3 = None
    if args.apply:
        import boto3

        s3 = boto3.client("s3")

    total_bytes = 0
    for path in files:
        key = path.relative_to(out_dir).as_posix()
        size = path.stat().st_size
        total_bytes += size
        print(f"{'upload' if args.apply else 'would upload'} s3://{args.bucket or '<JT_DATA_BUCKET>'}/{key} ({size} bytes)")
        if s3 is not None:
            content_type = CONTENT_TYPES.get(path.suffix.lower())
            if content_type is None:
                content_type, _ = mimetypes.guess_type(path.name)
            extra_args = {"ContentType": content_type} if content_type else {}
            s3.upload_file(str(path), args.bucket, key, ExtraArgs=extra_args)

    print(f"{'uploaded' if args.apply else 'planned'} {len(files)} objects ({total_bytes} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
