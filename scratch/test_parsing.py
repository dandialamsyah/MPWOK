import os
import json
import gspread
import logging
from google.oauth2.service_account import Credentials

SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEET_NAME = "KAWAL MPW"
KATEGORI_CLOSED = ['CLOSE', 'CLOSED']

def get_worksheet(sheet_name):
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
    gc = gspread.authorize(creds)
    sh = gc.open(SHEET_NAME)
    return sh.worksheet(sheet_name)

def preprocess_sheet_rows(rows):
    if not rows:
        return rows
    for i, row in enumerate(rows):
        row_upper = [str(cell).upper().strip() for cell in row]
        has_status = any(s_col in row_upper for s_col in ['STATUS', 'STATE'])
        has_incident = any(i_col in row_upper for i_col in ['INCIDENT', 'WONUM', 'TICKET ID', 'NO TIKET'])
        if has_status and has_incident:
            print(f"Found headers at row {i}: {row}")
            return rows[i:]
    return rows

def resolve_headers(header):
    idx_status = -1
    for s_col in ['STATUS', 'STATE']:
        if s_col in header:
            idx_status = header.index(s_col)
            break
            
    idx_team = -1
    for t_col in ['TEAM', 'TEKNISI', 'PETUGAS']:
        if t_col in header:
            idx_team = header.index(t_col)
            break
            
    idx_incident = -1
    for i_col in ['INCIDENT', 'WONUM', 'TICKET ID', 'NO TIKET']:
        if i_col in header:
            idx_incident = header.index(i_col)
            break
            
    idx_device = -1
    for d_col in ['DEVICE NAME', 'ALPRO', 'ODP']:
        if d_col in header:
            idx_device = header.index(d_col)
            break
            
    idx_cust_type = -1
    for c_col in ['CUSTOMER TYPE', 'TIPE PELANGGAN', 'PRIORITAS', 'CLASS']:
        if c_col in header:
            idx_cust_type = header.index(c_col)
            break
            
    return idx_status, idx_team, idx_incident, idx_device, idx_cust_type

def test_sheet(sheet_name):
    print(f"\n--- Testing sheet: {sheet_name} ---")
    ws = get_worksheet(sheet_name)
    raw_rows = ws.get_all_values()
    print(f"Raw rows count: {len(raw_rows)}")
    rows = preprocess_sheet_rows(raw_rows)
    print(f"Processed rows count: {len(rows)}")
    
    if len(rows) < 2:
        print("Empty sheet after preprocess")
        return
        
    header = [str(h).upper().strip() for h in rows[0]]
    idx_status, idx_team, idx_incident, idx_device, idx_cust_type = resolve_headers(header)
    print(f"Resolved columns -> status: {idx_status}, team: {idx_team}, incident: {idx_incident}, device: {idx_device}, cust_type: {idx_cust_type}")
    
    # Test open tickets count
    open_count = 0
    closed_count = 0
    for row in rows[1:]:
        if len(row) <= max(idx_status, idx_team, idx_incident):
            continue
        incident = str(row[idx_incident]).strip()
        if not incident:
            continue
        status_raw = str(row[idx_status]).upper().strip()
        if any(x in status_raw for x in KATEGORI_CLOSED):
            closed_count += 1
        else:
            open_count += 1
    print(f"Found {open_count} open tickets and {closed_count} closed tickets.")

if __name__ == "__main__":
    test_sheet("sta")
    test_sheet("UNDSEPC STA")
