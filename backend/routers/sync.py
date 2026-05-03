import json
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from utils import google_sdk, extractor
from utils.security import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

class SyncRequest(BaseModel):
    sheet_url: str
    folder_url: str

def _emit(event: dict) -> str:
    """Serialize a dict as a newline-delimited JSON line."""
    return json.dumps(event) + "\n"

@router.post("/sync")
def trigger_sync(request: SyncRequest, current_user: dict = Depends(get_current_user)):
    google_token = current_user.get("google_token")
    if not google_token:
        raise HTTPException(status_code=401, detail="No Google OAuth token found. Please re-login.")

    try:
        rows, headers, sheet_id, sheet_name = google_sdk.fetch_sheet_data(request.sheet_url, google_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google Sheet Error: {str(e)}")

    if not rows:
        def empty_stream():
            yield _emit({"type": "complete", "certificates": [], "errors": [], "newly_processed": 0, "loaded_from_cache": 0})
        return StreamingResponse(empty_stream(), media_type="application/x-ndjson")

    try:
        col_map = google_sdk.ensure_extracted_columns(sheet_id, sheet_name, headers, google_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not prepare sheet columns: {str(e)}")

    # Split rows upfront so we know exactly how many need processing
    cached_rows = []
    new_rows = []
    for row in rows:
        name = row.get("employee name", row.get("name", ""))
        email = row.get("email address", row.get("email id", row.get("email", "")))
        if not name and not email:
            continue
        sync_status = row.get("sync status", "").strip().lower()
        if sync_status == "processed":
            cached_rows.append(row)
        else:
            doc_url = row.get("upload doc", row.get("upload document", ""))
            file_id = google_sdk.parse_drive_file_id(doc_url) if doc_url else None
            if doc_url and file_id:
                new_rows.append(row)

    total_to_process = len(new_rows)

    def event_stream():
        results = []
        errors = []

        # ── Emit start event so frontend knows totals ──
        yield _emit({
            "type": "start",
            "total_new": total_to_process,
            "total_cached": len(cached_rows),
        })

        # ── Load cached rows instantly (no AI needed) ──
        for row in cached_rows:
            email = row.get("email address", row.get("email id", row.get("email", "")))
            name = row.get("employee name", row.get("name", ""))
            doc_url = row.get("upload doc", row.get("upload document", ""))
            cert_data = {
                "employee_name": name,
                "email": email,
                "certification_name": row.get("certification name", ""),
                "issuer": row.get("issuer", ""),
                "valid_from": row.get("valid from", ""),
                "valid_to": row.get("valid to", ""),
                "certificate_id": row.get("certificate id", ""),
                "doc_url": doc_url,
                "source": "cache",
            }
            results.append(cert_data)

        # ── Process new rows one by one, emitting progress each time ──
        for idx, row in enumerate(new_rows):
            email = row.get("email address", row.get("email id", row.get("email", "")))
            name = row.get("employee name", row.get("name", ""))
            doc_url = row.get("upload doc", row.get("upload document", ""))
            file_id = google_sdk.parse_drive_file_id(doc_url)

            try:
                file_bytes = google_sdk.download_drive_file(file_id, google_token)
                filename = f"drive_{file_id}.pdf"
                extracted = extractor.extract_certificate_details(file_bytes, filename)

                cert_data = {
                    "employee_name": name,
                    "email": email,
                    "certificate_id": extracted.get("certificate_id"),
                    "certification_name": extracted.get("certification_name"),
                    "issuer": extracted.get("issuer"),
                    "valid_from": extracted.get("valid_from"),
                    "valid_to": extracted.get("valid_to"),
                    "doc_url": doc_url,
                    "source": "new",
                }
                results.append(cert_data)

                # Write back to sheet
                row_index = row.get("__row_index__")
                if row_index:
                    try:
                        google_sdk.write_extracted_data_to_row(
                            sheet_id, sheet_name, row_index, col_map, extracted, google_token
                        )
                    except Exception as wb_err:
                        print(f"Warning: Write-back failed for row {row_index}: {wb_err}")

            except Exception as e:
                errors.append(f"Failed to process {name}: {str(e)}")

            # Emit progress after each row (done = rows completed so far)
            yield _emit({
                "type": "progress",
                "done": idx + 1,
                "total": total_to_process,
            })

        # ── Final event with full results ──
        yield _emit({
            "type": "complete",
            "certificates": results,
            "errors": errors,
            "newly_processed": len(new_rows),
            "loaded_from_cache": len(cached_rows),
        })

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("/certificates")
def get_admin_certificates():
    return []
