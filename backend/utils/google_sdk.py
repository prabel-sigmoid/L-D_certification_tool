import os
import re
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]

# These are the columns we write back to the sheet after AI extraction.
# They act as a persistent cache — the "database" columns.
EXTRACTED_COLUMNS = [
    "Sync Status",
    "Certification Name",
    "Issuer",
    "Valid From",
    "Valid To",
    "Certificate ID",
]
EXTRACTED_COLUMNS_LOWER = [c.lower() for c in EXTRACTED_COLUMNS]


def get_google_services(google_token: str):
    if not google_token:
        raise ValueError("Missing Google OAuth token. the user must login.")
        
    creds = Credentials(google_token)
    sheets_service = build('sheets', 'v4', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return sheets_service, drive_service


def parse_sheet_id(url: str) -> str:
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else url


def parse_drive_file_id(url: str) -> str:
    match = re.search(r'id=([a-zA-Z0-9-_]+)', url)
    if match: return match.group(1)
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else url


def fetch_sheet_data(sheet_url: str, google_token: str) -> tuple:
    sheet_id = parse_sheet_id(sheet_url)
    sheets_service, _ = get_google_services(google_token)
    
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheets = sheet_metadata.get('sheets', '')
    first_sheet_name = sheets[0].get("properties", {}).get("title", "Sheet1")
    
    range_name = f"{first_sheet_name}!A:Z"
    
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=range_name).execute()
    
    rows = result.get('values', [])
    if not rows:
        return [], [], sheet_id, first_sheet_name

    # Map headers to rows
    headers = [h.strip().lower() for h in rows[0]]
    data = []
    
    for row_idx, row in enumerate(rows[1:], start=2):  # row 1 is the header
        # Pad row with empty strings if shorter than headers
        padded_row = row + [''] * (len(headers) - len(row))
        row_dict = {headers[i]: padded_row[i] for i in range(len(headers))}
        row_dict["__row_index__"] = row_idx
        data.append(row_dict)
        
    return data, headers, sheet_id, first_sheet_name


def download_drive_file(file_id: str, google_token: str) -> bytes:
    _, drive_service = get_google_services(google_token)
    
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    
    while done is False:
        status, done = downloader.next_chunk()
        
    return fh.getvalue()


def _col_index_to_letter(index: int) -> str:
    """Convert 0-indexed column number to Excel-style letter (0=A, 25=Z, 26=AA)."""
    result = ""
    while True:
        result = chr(index % 26 + ord('A')) + result
        index = index // 26 - 1
        if index < 0:
            break
    return result


def update_sheet_cell(sheet_id: str, sheet_name: str, cell_range: str, value: str, google_token: str):
    """Update a single cell in the Google Sheet."""
    sheets_service, _ = get_google_services(google_token)
    full_range = f"{sheet_name}!{cell_range}"
    body = {"values": [[value]]}
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=full_range,
        valueInputOption="RAW",
        body=body
    ).execute()


def ensure_extracted_columns(sheet_id: str, sheet_name: str, headers: list, google_token: str) -> dict:
    """
    Ensure all EXTRACTED_COLUMNS headers exist in the sheet.
    Creates any missing ones at the end.
    Returns a dict: { 'sync status': col_index, 'certification name': col_index, ... }
    """
    sheets_service, _ = get_google_services(google_token)
    col_map = {}
    headers_mutable = list(headers)  # don't mutate the original

    new_headers_to_write = []  # (col_index, display_name)

    for col_display in EXTRACTED_COLUMNS:
        col_lower = col_display.lower()
        if col_lower in headers_mutable:
            col_map[col_lower] = headers_mutable.index(col_lower)
        else:
            new_index = len(headers_mutable)
            col_map[col_lower] = new_index
            new_headers_to_write.append((new_index, col_display))
            headers_mutable.append(col_lower)

    # Batch-write any new headers in a single API call
    if new_headers_to_write:
        for col_index, col_display in new_headers_to_write:
            col_letter = _col_index_to_letter(col_index)
            update_sheet_cell(sheet_id, sheet_name, f"{col_letter}1", col_display, google_token)

    return col_map


def write_extracted_data_to_row(
    sheet_id: str,
    sheet_name: str,
    row_index: int,
    col_map: dict,
    extracted: dict,
    google_token: str
):
    """
    Write all extracted fields + 'Processed' flag to a single sheet row
    using a single batchUpdate API call for efficiency.
    """
    sheets_service, _ = get_google_services(google_token)

    # Map our extracted keys to the sheet column indices
    field_map = {
        "sync status":        "Processed",
        "certification name": extracted.get("certification_name") or "",
        "issuer":             extracted.get("issuer") or "",
        "valid from":         extracted.get("valid_from") or "",
        "valid to":           extracted.get("valid_to") or "",
        "certificate id":     extracted.get("certificate_id") or "",
    }

    data_updates = []
    for field_lower, value in field_map.items():
        if field_lower in col_map:
            col_letter = _col_index_to_letter(col_map[field_lower])
            cell_range = f"{sheet_name}!{col_letter}{row_index}"
            data_updates.append({
                "range": cell_range,
                "values": [[value]]
            })

    if data_updates:
        body = {
            "valueInputOption": "RAW",
            "data": data_updates
        }
        sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id,
            body=body
        ).execute()
