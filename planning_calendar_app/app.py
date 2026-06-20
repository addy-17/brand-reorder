import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)

# Database setup
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calendar.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            brand TEXT DEFAULT '',
            task TEXT DEFAULT '',
            content TEXT DEFAULT '',
            status TEXT DEFAULT 'planned',
            notes TEXT DEFAULT '',
            checklist TEXT DEFAULT '[]',
            image TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)')
    conn.commit()
    conn.close()

init_db()

# ===== API ENDPOINTS =====

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/events', methods=['GET'])
def get_events():
    conn = get_db()
    rows = conn.execute('SELECT * FROM events').fetchall()
    conn.close()
    
    events = {}
    for row in rows:
        d = row['date']
        if d not in events:
            events[d] = []
        events[d].append({
            'id': row['id'],
            'brand': row['brand'],
            'task': row['task'],
            'content': row['content'],
            'status': row['status'],
            'notes': row['notes'],
            'checklist': json.loads(row['checklist']) if row['checklist'] else [],
            'image': row['image'],
            'createdAt': row['created_at']
        })
    return jsonify(events)

@app.route('/api/events', methods=['POST'])
def add_event():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    event_id = data.get('id', 'ev_' + str(int(datetime.now().timestamp() * 1000)) + '_' + os.urandom(2).hex())
    date = data.get('date', '')
    if not date:
        return jsonify({'error': 'Date is required'}), 400
    
    conn = get_db()
    conn.execute('''
        INSERT OR REPLACE INTO events (id, date, brand, task, content, status, notes, checklist, image, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        event_id,
        date,
        data.get('brand', ''),
        data.get('task', ''),
        data.get('content', ''),
        data.get('status', 'planned'),
        data.get('notes', ''),
        json.dumps(data.get('checklist', [])),
        data.get('image', ''),
        data.get('createdAt', datetime.now().isoformat())
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'id': event_id})

@app.route('/api/events/<event_id>', methods=['PUT'])
def update_event(event_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    conn = get_db()
    existing = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    
    if existing:
        # Update existing event
        conn.execute('''
            UPDATE events SET date=?, brand=?, task=?, content=?, status=?, notes=?, checklist=?, image=?
            WHERE id=?
        ''', (
            data.get('date', existing['date']),
            data.get('brand', existing['brand']),
            data.get('task', existing['task']),
            data.get('content', existing['content']),
            data.get('status', existing['status']),
            data.get('notes', existing['notes']),
            json.dumps(data.get('checklist', json.loads(existing['checklist'] or '[]'))),
            data.get('image', existing['image']),
            event_id
        ))
    else:
        # Insert as new
        conn.execute('''
            INSERT INTO events (id, date, brand, task, content, status, notes, checklist, image, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_id,
            data.get('date', ''),
            data.get('brand', ''),
            data.get('task', ''),
            data.get('content', ''),
            data.get('status', 'planned'),
            data.get('notes', ''),
            json.dumps(data.get('checklist', [])),
            data.get('image', ''),
            data.get('createdAt', datetime.now().isoformat())
        ))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/events/<event_id>', methods=['DELETE'])
def delete_event(event_id):
    conn = get_db()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/events/move', methods=['POST'])
def move_event():
    data = request.get_json()
    event_id = data.get('id')
    new_date = data.get('date')
    if not event_id or not new_date:
        return jsonify({'error': 'Missing id or date'}), 400
    
    conn = get_db()
    conn.execute('UPDATE events SET date = ? WHERE id = ?', (new_date, event_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
