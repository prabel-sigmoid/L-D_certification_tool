from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from utils import storage, extractor
from datetime import datetime, timedelta

router = APIRouter(prefix="/certificates", tags=["certificates"])

CERTIFICATES = []  # mock DB, but file storage now in Azure Blob


@router.get("/")
def list_certificates():
    return CERTIFICATES


@router.post("/upload")
def upload_certificate(file: UploadFile = File(...)):
    blob_name = f"{datetime.utcnow().timestamp()}_{file.filename}"
    
    file.file.seek(0)
    file_bytes = file.file.read()

    # Upload to Azure Blob
    file.file.seek(0)
    blob_url = storage.upload_file_to_blob(file.file, blob_name)
    
    print(f"Extracting details from {file.filename}...")
    extracted = extractor.extract_certificate_details(file_bytes, file.filename)

    cert = {
        "id": len(CERTIFICATES) + 1,
        "username": "testuser@sigmoidanalytics.com",
        "certificate_name": file.filename,
        "certificate_id": extracted.get("certificate_id") or f"CERT-{len(CERTIFICATES)+1}",
        "platform": extracted.get("platform") or "Unknown",
        "issuer": extracted.get("issuer") or "Unknown",
        "valid_from": extracted.get("valid_from") or datetime.utcnow().strftime("%Y-%m-%d"),
        "valid_to": extracted.get("valid_to") or (datetime.utcnow() + timedelta(days=365)).strftime("%Y-%m-%d"),
        "blob_name": blob_name,
        "blob_url": blob_url,
    }
    CERTIFICATES.append(cert)
    return {"message": "Uploaded ✅", "certificate": cert}


@router.delete("/{cert_id}")
def delete_certificate(cert_id: int):
    global CERTIFICATES
    cert = next((c for c in CERTIFICATES if c["id"] == cert_id), None)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    # Delete from blob
    storage.delete_file_from_blob(cert["blob_name"])

    # Delete from memory
    CERTIFICATES = [c for c in CERTIFICATES if c["id"] != cert_id]
    return {"message": f"Certificate {cert_id} deleted ✅"}


@router.get("/download/{cert_id}")
def download_certificate(cert_id: int):
    cert = next((c for c in CERTIFICATES if c["id"] == cert_id), None)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    file_stream = storage.download_file_from_blob(cert["blob_name"])
    return StreamingResponse(file_stream, media_type="application/octet-stream", headers={
        "Content-Disposition": f"attachment; filename={cert['certificate_name']}"
    })
