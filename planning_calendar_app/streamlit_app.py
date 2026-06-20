import streamlit as st
from datetime import datetime, date
import calendar
import json
import os
import base64
import hashlib
import urllib.request
import urllib.error

# ===== PAGE CONFIG =====
st.set_page_config(page_title="Planning Calendar", page_icon="📅", layout="wide", initial_sidebar_state="collapsed")

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    .stApp { background: #0a0a1a; color: #f1f5f9; }
    #MainMenu, footer, header { visibility: hidden; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>select, .stDateInput>div>div>input {
        background: rgba(255,255,255,0.06) !important; border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 10px !important; color: #f1f5f9 !important;
    }
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus { border-color: #8b5cf6 !important; box-shadow: 0 0 0 3px rgba(139,92,246,0.3) !important; }
    .stButton>button { background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; transition: all 0.25s ease !important; }
    .stButton>button:hover { transform: translateY(-2px) !important; box-shadow: 0 6px 25px rgba(139,92,246,0.3) !important; }
    .stButton>button[kind="secondary"] { background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(255,255,255,0.08) !important; color: #94a3b8 !important; }
    h1, h2, h3 { color: #f1f5f9 !important; }
    .event-card { background: rgba(255,255,255,0.04); border-radius: 10px; padding: 14px; margin-bottom: 10px; border-left: 3px solid #8b5cf6; transition: all 0.25s ease; }
    .event-card:hover { background: rgba(255,255,255,0.07); }
    .ev-brand { font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px; }
    .brand-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    .ev-task { font-size: 13px; color: #94a3b8; margin: 4px 0; }
    .ev-meta { display: flex; gap: 8px; font-size: 11px; color: #64748b; flex-wrap: wrap; }
    .status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }
    .month-title { font-size: 24px; font-weight: 700; text-align: center; padding: 10px 0; }
    .cal-header { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
    .cal-header div { text-align: center; font-weight: 600; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; padding: 6px 0; }
    .stats-bar { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 12px 20px; font-size: 12px; color: #64748b; margin-top: 16px; }
    hr { border-color: rgba(255,255,255,0.08) !important; margin: 16px 0 !important; }
</style>
""", unsafe_allow_html=True)

# ===== SUPABASE CONFIG (from secrets or env) =====
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))
SUPABASE_BUCKET = "events"

# ===== DATA LAYER =====
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calendar_data.json')

def supabase_request(method, endpoint, data=None):
    """Make REST API call to Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    try:
        if method == "GET":
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        elif method == "POST":
            data_bytes = json.dumps(data).encode()
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode()) if resp.read() else {"success": True}
        elif method == "DELETE":
            req = urllib.request.Request(url, headers=headers, method="DELETE")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"success": True}
        elif method == "PATCH":
            data_bytes = json.dumps(data).encode()
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="PATCH")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"success": True}
    except urllib.error.HTTPError as e:
        if e.code == 406:
            return []
        st.warning(f"Supabase error ({method} {endpoint}): {e.code}")
        return None
    except Exception as e:
        st.warning(f"Supabase connection error: {e}")
        return None

def load_from_supabase():
    """Load all events from Supabase"""
    rows = supabase_request("GET", "events?select=*")
    if rows is None:
        return None
    
    events = {}
    for row in rows:
        d = row.get("date", "")
        if not d:
            continue
        checklist = []
        try:
            checklist = json.loads(row.get("checklist", "[]"))
        except:
            checklist = []
        event = {
            "id": row.get("id", ""),
            "brand": row.get("brand", ""),
            "task": row.get("task", ""),
            "content": row.get("content", ""),
            "status": row.get("status", "planned"),
            "notes": row.get("notes", ""),
            "checklist": checklist,
            "image": row.get("image", ""),
        }
        if d not in events:
            events[d] = []
        events[d].append(event)
    return events

def save_to_supabase(events):
    """Full sync: delete all and re-insert"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    
    # Delete all
    supabase_request("DELETE", "events?id=neq.none")
    
    # Insert all
    all_rows = []
    for date_str, ev_list in events.items():
        for ev in ev_list:
            all_rows.append({
                "id": ev.get("id", gen_id()),
                "date": date_str,
                "brand": ev.get("brand", ""),
                "task": ev.get("task", ""),
                "content": ev.get("content", ""),
                "status": ev.get("status", "planned"),
                "notes": ev.get("notes", ""),
                "checklist": json.dumps(ev.get("checklist", [])),
                "image": ev.get("image", ""),
            })
    
    if all_rows:
        # Insert in batches of 50
        for i in range(0, len(all_rows), 50):
            batch = all_rows[i:i+50]
            result = supabase_request("POST", "events", batch)
            if result is None:
                return False
    return True

def load_data():
    """Load from Supabase first, fallback to local file"""
    if SUPABASE_URL and SUPABASE_KEY:
        data = load_from_supabase()
        if data is not None:
            return data
    # Fallback to local
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE) as f:
                return json.load(f)
    except:
        pass
    return {}

def save_data(events):
    """Save to both Supabase and local file"""
    st.session_state.events = events
    # Save locally
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(events, f, indent=2)
    except:
        pass
    # Save to Supabase if configured
    if SUPABASE_URL and SUPABASE_KEY:
        save_to_supabase(events)

# ===== SESSION STATE =====
for key in ['month', 'year', 'sel_date', 'events', 'mode', 'edit_ev', 'edit_date']:
    if key not in st.session_state:
        if key == 'month': st.session_state.month = datetime.now().month
        elif key == 'year': st.session_state.year = datetime.now().year
        elif key == 'sel_date': st.session_state.sel_date = datetime.now().strftime('%Y-%m-%d')
        elif key == 'events': st.session_state.events = load_data()
        elif key == 'mode': st.session_state.mode = 'view'

# ===== HELPERS =====
BRAND_COLORS = ['#8b5cf6','#10b981','#f59e0b','#ef4444','#3b82f6','#ec4899','#14b8a6','#f97316','#6366f1','#84cc16','#a855f7','#06b6d4','#e11d48','#d946ef','#22c55e']
STATUS_COLORS = {'planned':'#64748b','in-progress':'#3b82f6','ready':'#10b981','posted':'#8b5cf6'}
STATUS_LABELS = {'planned':'📋 Planned','in-progress':'🔄 Progress','ready':'✅ Ready','posted':'🚀 Posted'}

def get_brand_color(brand):
    if not brand: return BRAND_COLORS[0]
    h = 0
    for c in brand: h = ord(c) + ((h << 5) - h)
    return BRAND_COLORS[abs(h) % len(BRAND_COLORS)]

def gen_id():
    import random
    return 'ev_' + str(int(datetime.now().timestamp()*1000)) + '_' + format(random.randint(0,255),'02x')

# ===== HEADER =====
st.markdown('<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;"><div style="width:40px;height:40px;background:linear-gradient(135deg,#8b5cf6,#c084fc);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 4px 15px rgba(139,92,246,0.3);">📅</div><h1 style="font-size:20px;font-weight:700;margin:0;">Planning <span style="color:#8b5cf6;">Calendar</span></h1></div>', unsafe_allow_html=True)

# ===== MODE: VIEW =====
if st.session_state.mode == 'view':
    c1, c2, c3, c4, c5 = st.columns([1,1,3,1,1])
    with c1:
        if st.button("◀", key="pm", help="Previous month"):
            st.session_state.month -= 1
            if st.session_state.month < 1: st.session_state.month = 12; st.session_state.year -= 1
            st.rerun()
    with c2:
        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        sel_month = st.selectbox("Month", range(1,13), index=st.session_state.month-1, label_visibility="collapsed",
                                format_func=lambda x: months[x-1], key="m_sel")
        if sel_month != st.session_state.month: st.session_state.month = sel_month; st.rerun()
    with c3:
        months_full = ['January','February','March','April','May','June','July','August','September','October','November','December']
        st.markdown(f'<div class="month-title">{months_full[st.session_state.month-1]} {st.session_state.year}</div>', unsafe_allow_html=True)
    with c4:
        sel_year = st.selectbox("Year", range(datetime.now().year-5, datetime.now().year+6), 
                               index=5-(datetime.now().year - st.session_state.year), label_visibility="collapsed", key="y_sel")
        if sel_year != st.session_state.year: st.session_state.year = sel_year; st.rerun()
    with c5:
        if st.button("▶", key="nm", help="Next month"):
            st.session_state.month += 1
            if st.session_state.month > 12: st.session_state.month = 1; st.session_state.year += 1
            st.rerun()

    # Calendar grid
    cal = calendar.Calendar(calendar.MONDAY)
    month_days = list(cal.monthdays2calendar(st.session_state.year, st.session_state.month))
    today = datetime.now().strftime('%Y-%m-%d')
    sel = st.session_state.sel_date

    st.markdown('<div class="cal-header"><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div><div>Sun</div></div>', unsafe_allow_html=True)
    
    for week in month_days:
        cols = st.columns(7)
        for i, (day, wd) in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown('<div style="padding:8px 0;"></div>', unsafe_allow_html=True)
                    continue
                ds = f"{st.session_state.year}-{st.session_state.month:02d}-{day:02d}"
                evs = st.session_state.events.get(ds, [])
                ev_count = len(evs)
                if st.button(
                    f"{day}" + (f" ({ev_count})" if ev_count > 0 else ""),
                    key=f"d_{ds}", use_container_width=True,
                    type="secondary" if ds != sel else "primary"
                ):
                    st.session_state.sel_date = ds; st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # Events for selected date
    d = datetime.strptime(sel, '%Y-%m-%d')
    st.markdown(f"<h3>📋 Events for {d.strftime('%A, %B %d, %Y')}</h3>", unsafe_allow_html=True)
    
    if st.button("+ Add Event", use_container_width=True, key="add_main"):
        st.session_state.mode = 'add'; st.rerun()
    
    day_events = st.session_state.events.get(sel, [])
    if not day_events:
        st.markdown('<div style="color:#64748b;text-align:center;padding:30px 0;">✨ No events for this day<br><small>Click + Add Event to create one</small></div>', unsafe_allow_html=True)
    else:
        for ev in day_events:
            bc = get_brand_color(ev.get('brand',''))
            sts = ev.get('status','planned')
            sbg = STATUS_COLORS.get(sts,'#64748b')
            st.markdown(f'<div class="event-card" style="border-left-color:{bc};">', unsafe_allow_html=True)
            st.markdown(f'<div class="ev-brand"><span class="brand-dot" style="background:{bc}"></span>{ev.get("brand","No Brand")}</div>', unsafe_allow_html=True)
            if ev.get('task'): st.markdown(f'<div class="ev-task">{ev["task"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ev-meta"><span class="status-badge" style="background:{sbg};color:white;">{STATUS_LABELS.get(sts,sts)}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            cc1, cc2, cc3 = st.columns([3,1,1])
            with cc1: pass
            with cc2:
                if st.button("✏️ Edit", key=f"e_{ev['id']}", use_container_width=True):
                    st.session_state.edit_ev = ev; st.session_state.edit_date = sel; st.session_state.mode = 'edit'; st.rerun()
            with cc3:
                if st.button("🗑️", key=f"del_{ev['id']}"):
                    if sel in st.session_state.events:
                        st.session_state.events[sel] = [e for e in st.session_state.events[sel] if e['id'] != ev['id']]
                        if not st.session_state.events[sel]: del st.session_state.events[sel]
                        save_data(st.session_state.events); st.rerun()
            
            with st.expander("📝 Details"):
                if ev.get('image'):
                    try:
                        img_b64 = ev['image'].split(',')[1] if ev['image'].startswith('data:') else ev['image']
                        st.image(base64.b64decode(img_b64), use_container_width=True)
                    except: pass
                if ev.get('content'): st.markdown(f"**Content:** {ev['content']}")
                if ev.get('checklist'):
                    st.markdown("**Checklist:**")
                    for item in ev['checklist']:
                        st.markdown(f"{'✅' if item.get('done') else '⬜'} {item.get('text','')}")
                if ev.get('notes'): st.markdown(f"**Notes:** {ev['notes']}")

# ===== MODE: ADD / EDIT =====
if st.session_state.mode in ['add', 'edit']:
    st.markdown("---")
    is_edit = st.session_state.mode == 'edit'
    st.markdown(f"<h3>{'✏️ Edit Event' if is_edit else '➕ Add Event'}</h3>", unsafe_allow_html=True)
    
    if is_edit:
        ev = st.session_state.edit_ev
        def_b = ev.get('brand',''); def_t = ev.get('task',''); def_c = ev.get('content','')
        def_s = ev.get('status','planned'); def_n = ev.get('notes',''); def_cl = ev.get('checklist',[])
    else:
        def_b=''; def_t=''; def_c=''; def_s='planned'; def_n=''; def_cl=[]
    
    with st.form("ev_form"):
        brand = st.text_input("Brand Name", value=def_b, placeholder="e.g. Toscee")
        task = st.text_input("Task / Action", value=def_t, placeholder="e.g. Shoot video")
        content = st.text_area("Post Content", value=def_c, placeholder="Write the caption...", height=80)
        status = st.selectbox("Status", ['planned','in-progress','ready','posted'],
                            format_func=lambda x: STATUS_LABELS.get(x,x),
                            index=['planned','in-progress','ready','posted'].index(def_s))
        img_file = st.file_uploader("Upload Image", type=['png','jpg','jpeg','gif'])
        notes = st.text_area("Notes", value=def_n, placeholder="Links, ideas...", height=60)
        
        st.markdown("**Checklist**")
        items = []
        n = st.number_input("Number of items", 0, 10, len(def_cl), 1, key="cl_n")
        for i in range(n):
            dt = def_cl[i].get('text','') if i < len(def_cl) else ''
            dd = def_cl[i].get('done',False) if i < len(def_cl) else False
            c1, c2 = st.columns([1,6])
            with c1: done = st.checkbox("", dd, key=f"cld_{i}")
            with c2: txt = st.text_input(f"Subtask {i+1}", dt, key=f"clt_{i}", label_visibility="collapsed")
            if txt: items.append({'text':txt,'done':done})
        
        if st.form_submit_button("💾 Save", use_container_width=True):
            if not brand: st.error("Brand name required")
            else:
                img_data = ""
                if img_file:
                    img_data = "data:image/png;base64," + base64.b64encode(img_file.getvalue()).decode()
                elif is_edit and ev.get('image'): img_data = ev['image']
                eid = ev.get('id', gen_id()) if is_edit else gen_id()
                nd = st.session_state.sel_date
                nev = {'id':eid,'brand':brand,'task':task,'content':content,'status':status,'notes':notes,'checklist':items,'image':img_data}
                
                if is_edit:
                    od = st.session_state.edit_date
                    if od in st.session_state.events:
                        st.session_state.events[od] = [e for e in st.session_state.events[od] if e['id'] != eid]
                        if not st.session_state.events[od]: del st.session_state.events[od]
                
                if nd not in st.session_state.events: st.session_state.events[nd] = []
                st.session_state.events[nd].append(nev)
                save_data(st.session_state.events)
                st.session_state.mode = 'view'; st.rerun()
    
    if st.button("← Cancel"): st.session_state.mode = 'view'; st.rerun()

# ===== STATUSBAR =====
total = sum(len(v) for v in st.session_state.events.values())
dates = len(st.session_state.events)
brands = set()
for el in st.session_state.events.values():
    for e in el:
        if e.get('brand'): brands.add(e['brand'])

legend = '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">'
for b in brands:
    c = get_brand_color(b)
    legend += f'<span style="display:flex;align-items:center;gap:4px;"><span style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block;"></span>{b}</span>'
legend += '</div>'

db_status = "🟢 Supabase connected" if (SUPABASE_URL and SUPABASE_KEY) else "🟡 Local storage only"
st.markdown(f'<div class="stats-bar"><div>Total Events: {total} • {dates} dates</div>{legend}<div style="font-size:10px;">{db_status}</div></div>', unsafe_allow_html=True)

# ===== SETUP INSTRUCTIONS (shown only when no Supabase configured) =====
if not SUPABASE_URL or not SUPABASE_KEY:
    with st.expander("⚙️ Setup Permanent Cloud Database (Supabase - Free)"):
        st.markdown("""
        **Step 1:** Go to [supabase.com](https://supabase.com) and sign up free
        
        **Step 2:** Create a new project → Copy your **Project URL** and **anon public key**
        
        **Step 3:** Run this SQL in Supabase SQL Editor:
        ```sql
        CREATE TABLE events (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            brand TEXT DEFAULT '',
            task TEXT DEFAULT '',
            content TEXT DEFAULT '',
            status TEXT DEFAULT 'planned',
            notes TEXT DEFAULT '',
            checklist TEXT DEFAULT '[]',
            image TEXT DEFAULT ''
        );
        CREATE INDEX idx_events_date ON events(date);
        ```
        
        **Step 4:** For Streamlit Cloud deployment, add to **Secrets**:
        ```
        SUPABASE_URL = "https://your-project.supabase.co"
        SUPABASE_KEY = "your-anon-key"
        ```
        
        **Step 5:** For local testing, set environment variables:
        ```
        set SUPABASE_URL=https://your-project.supabase.co
        set SUPABASE_KEY=your-anon-key
        ```
        """)
else:
    st.markdown(f'<div style="text-align:center;padding:8px 0;font-size:11px;color:#10b981;">✅ Data stored in Supabase cloud database — permanent, never lost</div>', unsafe_allow_html=True)

st.markdown(f'<div style="text-align:center;padding:12px 0;font-size:11px;color:#64748b;">Planning Calendar v2.0</div>', unsafe_allow_html=True)