import os
import time

import boto3

BUCKET = "what-oil-for-my-car-textract"
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "images")

s3 = boto3.client("s3")
textract = boto3.client("textract")


def ensure_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET)
    except s3.exceptions.ClientError:
        region = s3.meta.region_name
        if region and region != "us-east-1":
            s3.create_bucket(
                Bucket=BUCKET,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        else:
            s3.create_bucket(Bucket=BUCKET)


def upload(file_path, key):
    s3.upload_file(file_path, BUCKET, key)


def start_job(key):
    response = textract.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": BUCKET, "Name": key}},
        FeatureTypes=["TABLES"],
    )
    return response["JobId"]


def wait_for_job(job_id):
    while True:
        response = textract.get_document_analysis(JobId=job_id)
        status = response["JobStatus"]
        if status in ("SUCCEEDED", "FAILED", "PARTIAL_SUCCESS"):
            return response
        time.sleep(5)


def get_all_blocks(job_id):
    blocks = []
    response = textract.get_document_analysis(JobId=job_id)
    blocks.extend(response["Blocks"])
    while "NextToken" in response:
        response = textract.get_document_analysis(
            JobId=job_id, NextToken=response["NextToken"]
        )
        blocks.extend(response["Blocks"])
    return blocks


def print_tables(blocks, filename):
    block_map = {b["Id"]: b for b in blocks}
    tables = [b for b in blocks if b["BlockType"] == "TABLE"]
    print(f"\n=== {filename} — {len(tables)} table(s) found ===")
    for t_idx, table in enumerate(tables, 1):
        cells = {}
        for rel in table.get("Relationships", []):
            if rel["Type"] == "CHILD":
                for cid in rel["Ids"]:
                    cell = block_map[cid]
                    if cell["BlockType"] == "CELL":
                        text = ""
                        for r in cell.get("Relationships", []):
                            if r["Type"] == "CHILD":
                                for wid in r["Ids"]:
                                    w = block_map[wid]
                                    if w["BlockType"] in ("WORD", "SELECTION_ELEMENT"):
                                        text += w.get("Text", "") + " "
                        cells[(cell["RowIndex"], cell["ColumnIndex"])] = text.strip()
        if not cells:
            continue
        max_row = max(r for r, c in cells)
        max_col = max(c for r, c in cells)
        print(f"\n-- Table {t_idx} --")
        for r in range(1, max_row + 1):
            print("\t".join(cells.get((r, c), "") for c in range(1, max_col + 1)))


def process(file_path):
    filename = os.path.basename(file_path)
    key = f"input/{filename}"
    print(f"Uploading {filename}...")
    upload(file_path, key)
    print("Starting Textract job...")
    job_id = start_job(key)
    print(f"Waiting for job {job_id}...")
    result = wait_for_job(job_id)
    if result["JobStatus"] == "FAILED":
        print(f"FAILED: {filename}")
        return
    if result["JobStatus"] == "PARTIAL_SUCCESS":
        pages = sorted(
            {
                page
                for warning in result.get("Warnings", [])
                for page in warning.get("Pages", [])
            }
        )
        print(f"PARTIAL_SUCCESS: {filename} — affected pages: {pages or 'unknown'}")
    blocks = get_all_blocks(job_id)
    print_tables(blocks, filename)


if __name__ == "__main__":
    ensure_bucket()
    files = [os.path.join(IMAGES_DIR, f) for f in os.listdir(IMAGES_DIR)]
    for f in files:
        process(f)
