import http.server
import socketserver
import json
import logging
import os
import threading
from datetime import datetime, timezone, timedelta

# Import from config and sheets_handler
from config import KATEGORI_CLOSED, TEAM_LIST
import sheets_handler
from sheets_handler import (
    get_sheet_rows,
    resolve_headers,
    resolve_canonical_team,
    get_team_tags,
    get_open_tickets_data
)

# Set logging
logger = logging.getLogger(__name__)

# Cache helper functions from sheets_handler
def get_sheet_stats(sheet_name=None):
    rows = get_sheet_rows(sheet_name)
    if not rows or len(rows) < 2:
        return {"open": 0, "closed": 0, "total": 0, "resolution_rate": 0.0, "teams": []}
    
    header = [str(h).upper().strip() for h in rows[0]]
    idx_status, idx_team, idx_incident, _, _ = resolve_headers(header)
    
    if idx_status == -1 or idx_team == -1 or idx_incident == -1:
        return {"open": 0, "closed": 0, "total": 0, "resolution_rate": 0.0, "teams": []}
        
    total_open = 0
    total_closed = 0
    team_counts = {}
    
    # Initialize canonical teams
    for team in TEAM_LIST:
        team_counts[team] = {'open': 0, 'closed': 0, 'total': 0}
        
    unmapped_teams = {}
    
    for row in rows[1:]:
        if len(row) <= max(idx_status, idx_team, idx_incident):
            continue
        incident = str(row[idx_incident]).strip()
        if not incident:
            continue
        status_raw = str(row[idx_status]).upper().strip()
        team_raw = str(row[idx_team]).strip()
        
        is_closed = any(x in status_raw for x in KATEGORI_CLOSED)
        cat = 'closed' if is_closed else 'open'
        
        canonical_team = resolve_canonical_team(team_raw)
        if canonical_team:
            if canonical_team not in team_counts:
                team_counts[canonical_team] = {'open': 0, 'closed': 0, 'total': 0}
            team_counts[canonical_team][cat] += 1
            team_counts[canonical_team]['total'] += 1
        elif team_raw:
            if team_raw not in unmapped_teams:
                unmapped_teams[team_raw] = {'open': 0, 'closed': 0, 'total': 0}
            unmapped_teams[team_raw][cat] += 1
            unmapped_teams[team_raw]['total'] += 1
            
        if is_closed:
            total_closed += 1
        else:
            total_open += 1
            
    # Combine lists
    for ut, vals in unmapped_teams.items():
        team_counts[ut] = vals
        
    total = total_open + total_closed
    resolution_rate = (total_closed / total * 100) if total > 0 else 0.0
    
    # Sort teams by name, skip team with zero total tickets
    sorted_teams = []
    for team_name, counts in sorted(team_counts.items(), key=lambda x: x[0]):
        if counts['total'] > 0:
            sorted_teams.append({
                "name": team_name,
                "open": counts['open'],
                "closed": counts['closed'],
                "total": counts['total']
            })
        
    return {
        "open": total_open,
        "closed": total_closed,
        "total": total,
        "resolution_rate": round(resolution_rate, 1),
        "teams": sorted_teams
    }

def get_psb_stats():
    rows = get_sheet_rows("PSB")
    if not rows or len(rows) < 2:
        return {"total_akom": 0, "total_vakstar": 0, "grand_total": 0, "pic_summary": [], "sto_details": []}
    
    header = [str(h).strip().upper() for h in rows[0]]
    
    idx_sto = header.index('STO') if 'STO' in header else -1
    idx_akom = header.index('AKOM') if 'AKOM' in header else -1
    idx_vakstar = header.index('VAKSTAR') if 'VAKSTAR' in header else -1
    
    idx_pic = -1
    for i, h in enumerate(header):
        if h.startswith('PIC'):
            idx_pic = i
            break
            
    if idx_sto == -1 or idx_akom == -1 or idx_vakstar == -1 or idx_pic == -1:
        return {"total_akom": 0, "total_vakstar": 0, "grand_total": 0, "pic_summary": [], "sto_details": []}
        
    sto_list = []
    pic_summary = {}
    total_akom = 0
    total_vakstar = 0
    
    for row in rows[1:]:
        if len(row) <= max(idx_sto, idx_akom, idx_vakstar, idx_pic):
            continue
            
        sto = str(row[idx_sto]).strip()
        if not sto:
            continue
            
        try:
            akom_val = int(row[idx_akom]) if row[idx_akom] else 0
        except ValueError:
            akom_val = 0
            
        try:
            vakstar_val = int(row[idx_vakstar]) if row[idx_vakstar] else 0
        except ValueError:
            vakstar_val = 0
            
        pic = str(row[idx_pic]).strip() or "-"
        
        if akom_val > 0 or vakstar_val > 0:
            sto_list.append({
                'sto': sto,
                'akom': akom_val,
                'vakstar': vakstar_val,
                'pic': pic
            })
            
        pic_key = pic.upper()
        if pic_key != "-":
            if pic_key not in pic_summary:
                pic_summary[pic_key] = {'name': pic, 'akom': 0, 'vakstar': 0, 'total': 0}
            pic_summary[pic_key]['akom'] += akom_val
            pic_summary[pic_key]['vakstar'] += vakstar_val
            pic_summary[pic_key]['total'] += akom_val + vakstar_val
            
        total_akom += akom_val
        total_vakstar += vakstar_val
        
    sorted_pics = sorted(pic_summary.values(), key=lambda x: x['name'].upper())
    
    return {
        "total_akom": total_akom,
        "total_vakstar": total_vakstar,
        "grand_total": total_akom + total_vakstar,
        "pic_summary": sorted_pics,
        "sto_details": sto_list
    }

def compile_dashboard_data():
    tz_wib = timezone(timedelta(hours=7))
    now = datetime.now(tz_wib)
    
    # Safe data retrieval with try/except
    def safe_stats(name):
        try:
            return get_sheet_stats(name)
        except Exception as e:
            logger.error(f"Error fetching stats for '{name}': {e}")
            return {"open": 0, "closed": 0, "total": 0, "resolution_rate": 0.0, "teams": [], "error": str(e)}

    def safe_tickets(name):
        try:
            return get_open_tickets_data(name)
        except Exception as e:
            logger.error(f"Error fetching tickets for '{name}': {e}")
            return []

    # Get PSB stats safely
    try:
        psb_data = get_psb_stats()
    except Exception as e:
        logger.error(f"Error fetching PSB stats: {e}")
        psb_data = {"total_akom": 0, "total_vakstar": 0, "grand_total": 0, "pic_summary": [], "sto_details": [], "error": str(e)}

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "mpw": {
            "stats": safe_stats(None),
            "tickets": safe_tickets(None)
        },
        "sta": {
            "stats": safe_stats("sta"),
            "tickets": safe_tickets("sta")
        },
        "unspec_sta": {
            "stats": safe_stats("UNDSEPC STA"),
            "tickets": safe_tickets("UNDSEPC STA")
        },
        "urgent_mpw": {
            "stats": safe_stats("TIKET URGENT MPW"),
            "tickets": safe_tickets("TIKET URGENT MPW")
        },
        "urgent_sta": {
            "stats": safe_stats("TIKET URGENT STA"),
            "tickets": safe_tickets("TIKET URGENT STA")
        },
        "psb": psb_data
    }

# Single-Page HTML dashboard string
HTML_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MPWOK Bot Dashboard</title>
    <style>
        :root {
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --card-bg-hover: #252525;
            --header-bg: #1a1a1a;
            --border-color: #333333;
            --text-color: #e0e0e0;
            --text-muted: #888888;
            --text-white: #ffffff;
            
            /* Status Colors */
            --color-open: #ff4d4d;
            --color-closed: #2ecc71;
            --color-urgent: #f39c12;
            --color-sta: #3498db;
            --color-unspec: #9b59b6;
            
            /* Priority Badges */
            --badge-manja: #d32f2f;
            --badge-hvc: #f57c00;
            --badge-reguler: #475569;
            --badge-other: #334155;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            padding-bottom: 30px;
            font-size: 14px;
            line-height: 1.5;
        }

        header {
            background-color: var(--header-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 15px 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .header-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .logo-section h1 {
            font-size: 1.4rem;
            color: var(--text-white);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .logo-section p {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .controls-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .btn-refresh {
            background-color: #333333;
            color: var(--text-white);
            border: 1px solid var(--border-color);
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 600;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .btn-refresh:hover {
            background-color: #444444;
            border-color: #555555;
        }

        .btn-refresh:active {
            transform: scale(0.97);
        }

        .btn-refresh.loading {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .auto-refresh-container {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            color: var(--text-muted);
            user-select: none;
            cursor: pointer;
        }

        .auto-refresh-container input {
            cursor: pointer;
            accent-color: var(--color-closed);
            width: 16px;
            height: 16px;
        }

        .tabs-nav {
            background-color: #161616;
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 67px;
            z-index: 99;
            overflow-x: auto;
            white-space: nowrap;
            scrollbar-width: none; /* Firefox */
        }
        
        .tabs-nav::-webkit-scrollbar {
            display: none; /* Chrome/Safari */
        }

        .tabs-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
        }

        .tab-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 12px 18px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            position: relative;
            transition: color 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .tab-btn:hover {
            color: var(--text-color);
        }

        .tab-btn.active {
            color: var(--text-white);
        }

        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 3px;
            background-color: var(--color-closed);
            border-radius: 3px 3px 0 0;
        }

        .tab-badge {
            background-color: #333333;
            color: var(--text-white);
            font-size: 0.75rem;
            padding: 2px 6px;
            border-radius: 10px;
            font-weight: bold;
        }

        .tab-badge.has-open {
            background-color: var(--color-open);
        }

        main {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 15px;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s ease-in-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .alert-error {
            background-color: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #f87171;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 500;
        }

        /* Metric Cards */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }

        .metric-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 16px;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
            overflow: hidden;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background-color: var(--text-muted);
        }

        .metric-card.open::before { background-color: var(--color-open); }
        .metric-card.closed::before { background-color: var(--color-closed); }
        .metric-card.rate::before { background-color: #3b82f6; }
        .metric-card.urgent::before { background-color: var(--color-urgent); }

        .metric-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }

        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-white);
            margin: 8px 0;
            display: flex;
            align-items: baseline;
            gap: 6px;
        }

        .metric-sub {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Dashboard Overview Grid */
        .overview-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .overview-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px;
            transition: all 0.2s;
            cursor: pointer;
        }

        .overview-card:hover {
            background-color: var(--card-bg-hover);
            transform: translateY(-2px);
            border-color: #444444;
        }

        .overview-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }

        .overview-card-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-white);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .overview-stats {
            display: flex;
            justify-content: space-between;
            gap: 10px;
        }

        .overview-stat-item {
            text-align: center;
            flex: 1;
            padding: 8px;
            background-color: #161616;
            border-radius: 6px;
        }

        .overview-stat-item.open {
            border-bottom: 3px solid var(--color-open);
        }
        
        .overview-stat-item.closed {
            border-bottom: 3px solid var(--color-closed);
        }
        
        .overview-stat-item.rate {
            border-bottom: 3px solid #3b82f6;
        }

        .overview-stat-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-bottom: 4px;
            text-transform: uppercase;
        }

        .overview-stat-value {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-white);
        }

        /* Search Section */
        .search-bar-container {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
        }

        .search-input {
            flex: 1;
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            padding: 10px 14px;
            border-radius: 8px;
            outline: none;
            font-size: 0.9rem;
            transition: border-color 0.2s;
        }

        .search-input:focus {
            border-color: #555555;
            background-color: var(--card-bg-hover);
        }

        /* Section Layouts */
        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-white);
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .two-column-layout {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }

        @media (min-width: 768px) {
            .two-column-layout {
                grid-template-columns: 350px 1fr;
            }
        }

        /* Technician Tables */
        .table-container {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            overflow-x: auto;
            margin-bottom: 20px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            background-color: #1a1a1a;
            color: var(--text-white);
            font-weight: 600;
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        td {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr.table-total-row {
            background-color: #161616;
            font-weight: bold;
        }
        
        tr.table-total-row td {
            border-top: 2px solid var(--border-color);
            color: var(--text-white);
        }

        /* Ticket Cards for Mobile */
        .tickets-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .ticket-card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 14px;
            transition: all 0.2s;
            position: relative;
        }

        .ticket-card:hover {
            border-color: #444444;
        }

        .ticket-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            gap: 8px;
            margin-bottom: 8px;
        }

        .ticket-id {
            font-weight: 700;
            color: var(--text-white);
            font-size: 0.95rem;
        }

        .badge {
            font-size: 0.7rem;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .badge-status {
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--color-open);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        .badge-priority {
            background-color: var(--badge-other);
            color: #ffffff;
        }

        .badge-priority.manja {
            background-color: var(--badge-manja);
            box-shadow: 0 0 8px rgba(211, 47, 47, 0.4);
        }
        
        .badge-priority.hvc {
            background-color: var(--badge-hvc);
        }
        
        .badge-priority.reguler {
            background-color: var(--badge-reguler);
        }

        .ticket-details {
            display: grid;
            grid-template-columns: 1fr;
            gap: 6px;
            font-size: 0.85rem;
            margin-top: 8px;
        }

        @media (min-width: 576px) {
            .ticket-details {
                grid-template-columns: 1fr 1fr;
            }
        }

        .ticket-detail-item {
            display: flex;
            align-items: baseline;
            gap: 6px;
        }

        .detail-label {
            color: var(--text-muted);
            min-width: 80px;
            flex-shrink: 0;
            font-size: 0.8rem;
        }

        .detail-value {
            color: var(--text-color);
            font-weight: 500;
            word-break: break-all;
        }

        .detail-value.highlight {
            color: var(--text-white);
            font-weight: 600;
        }

        .detail-value.overdue {
            color: var(--color-open);
        }

        .detail-value.warning {
            color: var(--color-urgent);
        }

        .ticket-duration {
            font-size: 0.75rem;
            background-color: rgba(255, 255, 255, 0.05);
            padding: 2px 6px;
            border-radius: 4px;
            color: var(--text-muted);
            display: inline-block;
            margin-top: 4px;
        }

        .no-data {
            text-align: center;
            padding: 30px;
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-muted);
            font-weight: 500;
        }

        /* PSB Specific Styling */
        .psb-summary-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }
        
        @media (min-width: 768px) {
            .psb-summary-container {
                grid-template-columns: 1fr 1fr;
            }
        }

        .sto-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 10px;
        }

        .sto-card {
            background-color: #1a1a1a;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }

        .sto-name {
            font-weight: 700;
            color: var(--text-white);
            margin-bottom: 4px;
            font-size: 0.9rem;
        }

        .sto-pic {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-bottom: 6px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .sto-orders {
            display: flex;
            justify-content: center;
            gap: 8px;
            font-size: 0.75rem;
        }

        .sto-order-badge {
            padding: 1px 5px;
            border-radius: 3px;
            font-weight: bold;
        }

        .sto-order-badge.akom {
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--color-open);
        }

        .sto-order-badge.vakstar {
            background-color: rgba(46, 204, 113, 0.15);
            color: var(--color-closed);
        }

        footer {
            text-align: center;
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-top: 40px;
            border-top: 1px solid var(--border-color);
            padding-top: 15px;
        }
    </style>
</head>
<body>

    <header>
        <div class="header-container">
            <div class="logo-section">
                <h1>🎛️ MPWOK Dashboard</h1>
                <p id="last-updated-text">Memuat data...</p>
            </div>
            <div class="controls-section">
                <label class="auto-refresh-container">
                    <input type="checkbox" id="chk-auto-refresh" checked>
                    <span>Auto Refresh (30s)</span>
                </label>
                <button class="btn-refresh" id="btn-refresh-now">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                    <span>Refresh</span>
                </button>
            </div>
        </div>
    </header>

    <nav class="tabs-nav">
        <div class="tabs-container">
            <button class="tab-btn active" data-tab="tab-overview">📊 Ringkasan</button>
            <button class="tab-btn" data-tab="tab-mpw">🔴 MPW Assurance <span class="tab-badge" id="badge-count-mpw">0</span></button>
            <button class="tab-btn" data-tab="tab-sta">🔵 STA Assurance <span class="tab-badge" id="badge-count-sta">0</span></button>
            <button class="tab-btn" data-tab="tab-unspec">⚪ Unspec STA <span class="tab-badge" id="badge-count-unspec">0</span></button>
            <button class="tab-btn" data-tab="tab-urgent">🚨 Urgent <span class="tab-badge" id="badge-count-urgent">0</span></button>
            <button class="tab-btn" data-tab="tab-psb">🟢 PSB Active</button>
        </div>
    </nav>

    <main>
        <div id="error-container" style="display: none;"></div>

        <!-- TAB OVERVIEW -->
        <div id="tab-overview" class="tab-content active">
            <div class="overview-grid" id="overview-cards-container">
                <!-- Dynamic cards -->
            </div>
        </div>

        <!-- TAB MPW ASSURANCE -->
        <div id="tab-mpw" class="tab-content">
            <div class="metrics-grid" id="metrics-mpw"></div>
            <div class="search-bar-container">
                <input type="text" class="search-input" placeholder="Cari teknisi, no tiket, atau alpro..." data-target="tickets-mpw" oninput="filterTickets(this)">
            </div>
            <div class="two-column-layout">
                <div>
                    <h3 class="section-title">📊 Produktivitas Teknisi</h3>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Teknisi</th>
                                    <th style="text-align: center;">Open</th>
                                    <th style="text-align: center;">Closed</th>
                                    <th style="text-align: center;">Total</th>
                                </tr>
                            </thead>
                            <tbody id="tech-table-mpw"></tbody>
                        </table>
                    </div>
                </div>
                <div>
                    <h3 class="section-title">⚠️ Tiket Gangguan OPEN</h3>
                    <div class="tickets-list" id="tickets-mpw"></div>
                </div>
            </div>
        </div>

        <!-- TAB STA ASSURANCE -->
        <div id="tab-sta" class="tab-content">
            <div class="metrics-grid" id="metrics-sta"></div>
            <div class="search-bar-container">
                <input type="text" class="search-input" placeholder="Cari teknisi, no tiket, atau alpro..." data-target="tickets-sta" oninput="filterTickets(this)">
            </div>
            <div class="two-column-layout">
                <div>
                    <h3 class="section-title">📊 Produktivitas Teknisi</h3>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Teknisi</th>
                                    <th style="text-align: center;">Open</th>
                                    <th style="text-align: center;">Closed</th>
                                    <th style="text-align: center;">Total</th>
                                </tr>
                            </thead>
                            <tbody id="tech-table-sta"></tbody>
                        </table>
                    </div>
                </div>
                <div>
                    <h3 class="section-title">⚠️ Tiket Gangguan OPEN</h3>
                    <div class="tickets-list" id="tickets-sta"></div>
                </div>
            </div>
        </div>

        <!-- TAB UNSPEC STA -->
        <div id="tab-unspec" class="tab-content">
            <div class="metrics-grid" id="metrics-unspec"></div>
            <div class="search-bar-container">
                <input type="text" class="search-input" placeholder="Cari teknisi, no tiket, atau alpro..." data-target="tickets-unspec" oninput="filterTickets(this)">
            </div>
            <div class="two-column-layout">
                <div>
                    <h3 class="section-title">📊 Produktivitas Teknisi</h3>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Teknisi</th>
                                    <th style="text-align: center;">Open</th>
                                    <th style="text-align: center;">Closed</th>
                                    <th style="text-align: center;">Total</th>
                                </tr>
                            </thead>
                            <tbody id="tech-table-unspec"></tbody>
                        </table>
                    </div>
                </div>
                <div>
                    <h3 class="section-title">⚠️ Tiket Gangguan OPEN</h3>
                    <div class="tickets-list" id="tickets-unspec"></div>
                </div>
            </div>
        </div>

        <!-- TAB URGENT TICKETS -->
        <div id="tab-urgent" class="tab-content">
            <div class="metrics-grid">
                <div class="metric-card urgent">
                    <div>
                        <div class="metric-label">Urgent MPW Open</div>
                        <div class="metric-value" id="urgent-mpw-val">0</div>
                    </div>
                    <div class="metric-sub" id="urgent-mpw-rate">Res. Rate: 0%</div>
                </div>
                <div class="metric-card urgent">
                    <div>
                        <div class="metric-label">Urgent STA Open</div>
                        <div class="metric-value" id="urgent-sta-val">0</div>
                    </div>
                    <div class="metric-sub" id="urgent-sta-rate">Res. Rate: 0%</div>
                </div>
            </div>
            <div class="search-bar-container">
                <input type="text" class="search-input" placeholder="Cari teknisi, no tiket, atau alpro..." data-target="tickets-urgent" oninput="filterTickets(this)">
            </div>
            <div style="display: grid; grid-template-columns: 1fr; gap: 20px;">
                <div>
                    <h3 class="section-title">🚨 Daftar Tiket Urgent OPEN (MPW & STA)</h3>
                    <div class="tickets-list" id="tickets-urgent"></div>
                </div>
            </div>
        </div>

        <!-- TAB PSB -->
        <div id="tab-psb" class="tab-content">
            <div class="metrics-grid">
                <div class="metric-card open">
                    <div>
                        <div class="metric-label">Total Akom</div>
                        <div class="metric-value" id="psb-akom-val">0</div>
                    </div>
                    <div class="metric-sub">Order Pasang Baru (Akom)</div>
                </div>
                <div class="metric-card closed">
                    <div>
                        <div class="metric-label">Total Vakstar</div>
                        <div class="metric-value" id="psb-vakstar-val">0</div>
                    </div>
                    <div class="metric-sub">Order Pasang Baru (Vakstar)</div>
                </div>
                <div class="metric-card rate">
                    <div>
                        <div class="metric-label">Grand Total</div>
                        <div class="metric-value" id="psb-total-val">0</div>
                    </div>
                    <div class="metric-sub">Seluruh Order Aktif</div>
                </div>
            </div>

            <div class="psb-summary-container">
                <div>
                    <h3 class="section-title">👤 Rekap Per PIC</h3>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Nama PIC</th>
                                    <th style="text-align: center;">Akom</th>
                                    <th style="text-align: center;">Vakstar</th>
                                    <th style="text-align: center;">Total</th>
                                </tr>
                            </thead>
                            <tbody id="psb-pic-table"></tbody>
                        </table>
                    </div>
                </div>
                <div>
                    <h3 class="section-title">📍 Detail Per STO</h3>
                    <div class="sto-grid" id="psb-sto-grid"></div>
                </div>
            </div>
        </div>

    </main>

    <footer>
        <p>MPWOK Bot Dashboard &copy; 2026. Made with ❤️ for Assurance Mempawah.</p>
    </footer>

    <script>
        // DOM Elements
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        const btnRefresh = document.getElementById('btn-refresh-now');
        const chkAutoRefresh = document.getElementById('chk-auto-refresh');
        const lastUpdatedText = document.getElementById('last-updated-text');
        const errorContainer = document.getElementById('error-container');

        let autoRefreshInterval = null;

        // Init
        document.addEventListener('DOMContentLoaded', () => {
            // Tab Switcher
            tabButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    const targetTabId = btn.getAttribute('data-tab');
                    
                    tabButtons.forEach(b => b.classList.remove('active'));
                    tabContents.forEach(c => c.classList.remove('active'));
                    
                    btn.classList.add('active');
                    document.getElementById(targetTabId).classList.add('active');
                });
            });

            // Refresh Event
            btnRefresh.addEventListener('click', () => {
                fetchDashboardData(true);
            });

            // Auto Refresh Event
            chkAutoRefresh.addEventListener('change', (e) => {
                toggleAutoRefresh(e.target.checked);
            });

            // Initial Load
            fetchDashboardData(false);
            toggleAutoRefresh(chkAutoRefresh.checked);
        });

        function toggleAutoRefresh(enable) {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }
            if (enable) {
                autoRefreshInterval = setInterval(() => {
                    fetchDashboardData(false);
                }, 30000); // 30s
            }
        }

        async function fetchDashboardData(forceRefresh = false) {
            btnRefresh.classList.add('loading');
            btnRefresh.querySelector('span').innerText = forceRefresh ? 'Mengambil...' : 'Refreshing...';

            const url = forceRefresh ? '/api/refresh' : '/api/data';
            const method = forceRefresh ? 'POST' : 'GET';

            try {
                const response = await fetch(url, { method });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const result = await response.json();
                
                if (result.status === 'success') {
                    renderData(result.data);
                    errorContainer.style.display = 'none';
                } else {
                    showGlobalError(result.message || 'Gagal memuat data');
                }
            } catch (err) {
                console.error(err);
                showGlobalError(`Gagal terhubung ke server: ${err.message}`);
            } finally {
                btnRefresh.classList.remove('loading');
                btnRefresh.querySelector('span').innerText = 'Refresh';
            }
        }

        function showGlobalError(msg) {
            errorContainer.innerHTML = `
                <div class="alert-error">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    <span>${msg}</span>
                </div>
            `;
            errorContainer.style.display = 'block';
        }

        function getPriorityClass(prio) {
            const p = String(prio).toUpperCase();
            if (p.includes('MANJA')) return 'manja';
            if (p.includes('HVC') || p.includes('GOLD')) return 'hvc';
            if (p.includes('REGULER') || p.includes('REG')) return 'reguler';
            return '';
        }

        function filterTickets(input) {
            const val = input.value.toLowerCase().trim();
            const targetId = input.getAttribute('data-target');
            const container = document.getElementById(targetId);
            const cards = container.querySelectorAll('.ticket-card');

            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                if (text.includes(val)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        }

        function renderData(data) {
            // Update time
            lastUpdatedText.innerText = `Data diperbarui: ${data.timestamp} WIB`;

            // Update Badges
            document.getElementById('badge-count-mpw').innerText = data.mpw.tickets.length;
            document.getElementById('badge-count-sta').innerText = data.sta.tickets.length;
            document.getElementById('badge-count-unspec').innerText = data.unspec_sta.tickets.length;
            document.getElementById('badge-count-urgent').innerText = data.urgent_mpw.tickets.length + data.urgent_sta.tickets.length;

            const mpwHasOpen = data.mpw.tickets.length > 0;
            const staHasOpen = data.sta.tickets.length > 0;
            const unspecHasOpen = data.unspec_sta.tickets.length > 0;
            const urgentHasOpen = (data.urgent_mpw.tickets.length + data.urgent_sta.tickets.length) > 0;

            document.getElementById('badge-count-mpw').className = `tab-badge ${mpwHasOpen ? 'has-open' : ''}`;
            document.getElementById('badge-count-sta').className = `tab-badge ${staHasOpen ? 'has-open' : ''}`;
            document.getElementById('badge-count-unspec').className = `tab-badge ${unspecHasOpen ? 'has-open' : ''}`;
            document.getElementById('badge-count-urgent').className = `tab-badge ${urgentHasOpen ? 'has-open' : ''}`;

            // Render Overview Tab
            renderOverview(data);

            // Render Tab details
            renderAssuranceTab('mpw', data.mpw);
            renderAssuranceTab('sta', data.sta);
            renderAssuranceTab('unspec', data.unspec_sta);

            // Render Urgent Tab Specifics
            document.getElementById('urgent-mpw-val').innerText = data.urgent_mpw.tickets.length;
            document.getElementById('urgent-mpw-rate').innerText = `Res. Rate: ${data.urgent_mpw.stats.resolution_rate}%`;
            document.getElementById('urgent-sta-val').innerText = data.urgent_sta.tickets.length;
            document.getElementById('urgent-sta-rate').innerText = `Res. Rate: ${data.urgent_sta.stats.resolution_rate}%`;
            
            const urgentListContainer = document.getElementById('tickets-urgent');
            urgentListContainer.innerHTML = '';
            const allUrgent = [...data.urgent_mpw.tickets, ...data.urgent_sta.tickets];
            if (allUrgent.length === 0) {
                urgentListContainer.innerHTML = '<div class="no-data">✅ Semua tiket URGENT sudah closed!</div>';
            } else {
                allUrgent.forEach(t => {
                    urgentListContainer.appendChild(createTicketCard(t));
                });
            }

            // Render PSB Tab
            renderPSB(data.psb);
        }

        function renderOverview(data) {
            const container = document.getElementById('overview-cards-container');
            container.innerHTML = '';

            const sections = [
                { title: '🔴 MPW Assurance', id: 'tab-mpw', data: data.mpw.stats, openTickets: data.mpw.tickets.length },
                { title: '🔵 STA Assurance', id: 'tab-sta', data: data.sta.stats, openTickets: data.sta.tickets.length },
                { title: '⚪ Unspec STA', id: 'tab-unspec', data: data.unspec_sta.stats, openTickets: data.unspec_sta.tickets.length },
                { title: '🚨 Urgent MPW', id: 'tab-urgent', data: data.urgent_mpw.stats, openTickets: data.urgent_mpw.tickets.length },
                { title: '🚨 Urgent STA', id: 'tab-urgent', data: data.urgent_sta.stats, openTickets: data.urgent_sta.tickets.length },
                { title: '🟢 PSB (Pasang Baru)', id: 'tab-psb', data: { open: data.psb.total_akom, closed: data.psb.total_vakstar, total: data.psb.grand_total, resolution_rate: null } }
            ];

            sections.forEach(s => {
                const card = document.createElement('div');
                card.className = 'overview-card';
                card.onclick = () => {
                    document.querySelector(`[data-tab="${s.id}"]`).click();
                };

                let statsHtml = '';
                if (s.resolution_rate !== null && s.data.resolution_rate !== undefined) {
                    statsHtml = `
                        <div class="overview-stat-item open">
                            <div class="overview-stat-label">Open</div>
                            <div class="overview-stat-value">${s.data.open}</div>
                        </div>
                        <div class="overview-stat-item closed">
                            <div class="overview-stat-label">Closed</div>
                            <div class="overview-stat-value">${s.data.closed}</div>
                        </div>
                        <div class="overview-stat-item rate">
                            <div class="overview-stat-label">Res Rate</div>
                            <div class="overview-stat-value">${s.data.resolution_rate}%</div>
                        </div>
                    `;
                } else {
                    statsHtml = `
                        <div class="overview-stat-item open">
                            <div class="overview-stat-label">Akom</div>
                            <div class="overview-stat-value">${s.data.open}</div>
                        </div>
                        <div class="overview-stat-item closed">
                            <div class="overview-stat-label">Vakstar</div>
                            <div class="overview-stat-value">${s.data.closed}</div>
                        </div>
                        <div class="overview-stat-item rate">
                            <div class="overview-stat-label">Total</div>
                            <div class="overview-stat-value">${s.data.total}</div>
                        </div>
                    `;
                }

                card.innerHTML = `
                    <div class="overview-card-header">
                        <div class="overview-card-title">${s.title}</div>
                        ${s.openTickets !== undefined && s.openTickets > 0 ? `<span class="badge badge-status" style="background-color: var(--color-open); color: white;">${s.openTickets} Open</span>` : ''}
                    </div>
                    <div class="overview-stats">
                        ${statsHtml}
                    </div>
                `;
                container.appendChild(card);
            });
        }

        function renderAssuranceTab(prefix, tabData) {
            // Metrics grid
            const metricsContainer = document.getElementById(`metrics-${prefix}`);
            metricsContainer.innerHTML = `
                <div class="metric-card open">
                    <div>
                        <div class="metric-label">Open Tiket</div>
                        <div class="metric-value">${tabData.stats.open}</div>
                    </div>
                    <div class="metric-sub">Belum selesai</div>
                </div>
                <div class="metric-card closed">
                    <div>
                        <div class="metric-label">Closed Tiket</div>
                        <div class="metric-value">${tabData.stats.closed}</div>
                    </div>
                    <div class="metric-sub">Tiket selesai</div>
                </div>
                <div class="metric-card rate">
                    <div>
                        <div class="metric-label">Resolution Rate</div>
                        <div class="metric-value">${tabData.stats.resolution_rate}%</div>
                    </div>
                    <div class="metric-sub">Target penyelesaian</div>
                </div>
            `;

            // Tech table
            const tableBody = document.getElementById(`tech-table-${prefix}`);
            tableBody.innerHTML = '';
            if (tabData.stats.teams.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Tidak ada data teknisi</td></tr>';
            } else {
                tabData.stats.teams.forEach(t => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${t.name}</td>
                        <td style="text-align: center; font-weight: bold; color: ${t.open > 0 ? 'var(--color-open)' : 'inherit'};">${t.open}</td>
                        <td style="text-align: center; color: var(--text-muted);">${t.closed}</td>
                        <td style="text-align: center; font-weight: bold;">${t.total}</td>
                    `;
                    tableBody.appendChild(row);
                });
                
                // Add grand total row
                const totalRow = document.createElement('tr');
                totalRow.className = 'table-total-row';
                totalRow.innerHTML = `
                    <td>TOTAL</td>
                    <td style="text-align: center; color: var(--color-open);">${tabData.stats.open}</td>
                    <td style="text-align: center;">${tabData.stats.closed}</td>
                    <td style="text-align: center;">${tabData.stats.total}</td>
                `;
                tableBody.appendChild(totalRow);
            }

            // Tickets list
            const ticketsContainer = document.getElementById(`tickets-${prefix}`);
            ticketsContainer.innerHTML = '';
            if (tabData.tickets.length === 0) {
                ticketsContainer.innerHTML = '<div class="no-data">✅ Semua tiket gangguan sudah CLOSED!</div>';
            } else {
                tabData.tickets.forEach(t => {
                    ticketsContainer.appendChild(createTicketCard(t));
                });
            }
        }

        function createTicketCard(t) {
            const card = document.createElement('div');
            card.className = 'ticket-card';
            
            const prioClass = getPriorityClass(t.cust_type);
            const prioText = t.cust_type || 'REGULER';
            
            let ttrClass = '';
            if (t.ttr_remaining) {
                if (t.ttr_remaining.includes('lewat')) {
                    ttrClass = 'overdue';
                } else if (t.ttr_remaining.includes('menit') && !t.ttr_remaining.includes('jam') && !t.ttr_remaining.includes('hari')) {
                    ttrClass = 'warning';
                }
            }

            card.innerHTML = `
                <div class="ticket-header">
                    <span class="ticket-id">${t.incident}</span>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <span class="badge badge-status">${t.status}</span>
                        <span class="badge badge-priority ${prioClass}">${prioText}</span>
                    </div>
                </div>
                <div class="ticket-duration">${t.duration ? `durasi: ${t.duration}` : 'durasi baru'}</div>
                <div class="ticket-details">
                    <div class="ticket-detail-item">
                        <span class="detail-label">Teknisi</span>
                        <span class="detail-value highlight">${t.team || 'BLM ASSIGN'}</span>
                    </div>
                    <div class="ticket-detail-item">
                        <span class="detail-label">Alpro/ODP</span>
                        <span class="detail-value">${t.device || '-'}</span>
                    </div>
                    ${t.booking_date ? `
                    <div class="ticket-detail-item" style="grid-column: 1 / -1;">
                        <span class="detail-label">Booking</span>
                        <span class="detail-value">${t.booking_date} <span class="detail-value ${ttrClass}" style="margin-left: 5px; font-weight: bold;">(${t.ttr_remaining})</span></span>
                    </div>
                    ` : ''}
                </div>
            `;
            return card;
        }

        function renderPSB(psbData) {
            // Metrics
            document.getElementById('psb-akom-val').innerText = psbData.total_akom;
            document.getElementById('psb-vakstar-val').innerText = psbData.total_vakstar;
            document.getElementById('psb-total-val').innerText = psbData.grand_total;

            // PIC table
            const tableBody = document.getElementById('psb-pic-table');
            tableBody.innerHTML = '';
            if (psbData.pic_summary.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Tidak ada order aktif</td></tr>';
            } else {
                psbData.pic_summary.forEach(p => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${p.name}</td>
                        <td style="text-align: center; color: var(--color-open); font-weight: bold;">${p.akom}</td>
                        <td style="text-align: center; color: var(--color-closed); font-weight: bold;">${p.vakstar}</td>
                        <td style="text-align: center; font-weight: bold;">${p.total}</td>
                    `;
                    tableBody.appendChild(row);
                });
                
                // Grand total row
                const totalRow = document.createElement('tr');
                totalRow.className = 'table-total-row';
                totalRow.innerHTML = `
                    <td>TOTAL</td>
                    <td style="text-align: center; color: var(--color-open);">${psbData.total_akom}</td>
                    <td style="text-align: center; color: var(--color-closed);">${psbData.total_vakstar}</td>
                    <td style="text-align: center;">${psbData.grand_total}</td>
                `;
                tableBody.appendChild(totalRow);
            }

            // STO cards grid
            const stoGrid = document.getElementById('psb-sto-grid');
            stoGrid.innerHTML = '';
            if (psbData.sto_details.length === 0) {
                stoGrid.innerHTML = '<div class="no-data" style="grid-column: 1 / -1;">✅ Tidak ada order aktif per STO</div>';
            } else {
                psbData.sto_details.forEach(item => {
                    const card = document.createElement('div');
                    card.className = 'sto-card';
                    
                    let badgesHtml = '';
                    if (item.akom > 0) {
                        badgesHtml += `<span class="sto-order-badge akom">Akom: ${item.akom}</span> `;
                    }
                    if (item.vakstar > 0) {
                        badgesHtml += `<span class="sto-order-badge vakstar">Vak: ${item.vakstar}</span>`;
                    }

                    card.innerHTML = `
                        <div class="sto-name">${item.sto}</div>
                        <div class="sto-pic" title="${item.pic}">${item.pic}</div>
                        <div class="sto-orders">${badgesHtml}</div>
                    `;
                    stoGrid.appendChild(card);
                });
            }
        }
    </script>
</body>
</html>
"""

class DashboardRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Redirect http server logs to standard logger
        logger.info("%s - - %s" % (self.client_address[0], format%args))

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
            
        elif self.path == "/api/data":
            try:
                data = compile_dashboard_data()
                payload = {
                    "status": "success",
                    "data": data
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode('utf-8'))
            except Exception as e:
                logger.error(f"Error serving /api/data: {e}")
                self.send_error_json(500, f"Internal Server Error: {str(e)}")
                
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def do_POST(self):
        if self.path == "/api/refresh":
            try:
                # Clear gspread cache
                sheets_handler.clear_cache()
                
                # Fetch fresh data
                data = compile_dashboard_data()
                payload = {
                    "status": "success",
                    "data": data
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode('utf-8'))
            except Exception as e:
                logger.error(f"Error performing /api/refresh: {e}")
                self.send_error_json(500, f"Internal Server Error during refresh: {str(e)}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def send_error_json(self, code, message):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {
            "status": "error",
            "message": message
        }
        self.wfile.write(json.dumps(payload).encode('utf-8'))

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def start_dashboard_server():
    port = int(os.environ.get("PORT", 5000))
    server_address = ('0.0.0.0', port)
    
    try:
        httpd = ThreadingHTTPServer(server_address, DashboardRequestHandler)
        logger.info(f"Dashboard Web Server running on http://0.0.0.0:{port} ...")
        httpd.serve_forever()
    except Exception as e:
        logger.critical(f"Failed to start dashboard web server on port {port}: {e}")
