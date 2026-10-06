import http.server
import socketserver
import sqlite3
import json
import uuid
import hashlib
import secrets
import webbrowser
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HOST = "127.0.0.1"
PORT = 8000
APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "lostnomore.db"

SESSIONS = {}  # session token -> user dict


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def row_to_report(row):
    keys = ["id", "type", "name", "email", "phone", "site", "location", "date",
            "items", "description", "reward", "imageData", "hiddenInfo", "timestamp"]
    data = dict(zip(keys, row))
    data["hiddenInfo"] = bool(data["hiddenInfo"])
    return data


def row_to_user(row):
    keys = ["id", "name", "email", "phone", "role", "createdAt"]
    data = dict(zip(keys, row))
    data["isAdmin"] = data["role"] == "admin"
    return data


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            phone TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL CHECK(type IN ('Lost', 'Found')),
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            site TEXT DEFAULT '',
            location TEXT DEFAULT '',
            date TEXT DEFAULT '',
            items TEXT NOT NULL,
            description TEXT DEFAULT '',
            reward TEXT DEFAULT '',
            image_data TEXT,
            hidden_info INTEGER NOT NULL DEFAULT 0,
            timestamp TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(type);
        CREATE INDEX IF NOT EXISTS idx_reports_email ON reports(email);
        CREATE INDEX IF NOT EXISTS idx_reports_site ON reports(site);
        CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(date);
    """)
    admin = conn.execute("SELECT id FROM users WHERE email = ?", ("admin@gmail.com",)).fetchone()
    if not admin:
        conn.execute(
            """INSERT INTO users (name, email, phone, password_hash, role, created_at)
               VALUES (?, ?, ?, ?, 'admin', ?)""",
            ("Administrator", "admin@gmail.com", "", hash_password("admin123"), now_iso())
        )
    conn.commit()
    conn.close()


def import_legacy_data(payload):
    """One-time import from the previous browser localStorage version."""
    reports = payload.get("reports") or []
    users = payload.get("users") or []
    conn = db()
    existing_reports = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
    imported_reports = 0
    imported_users = 0

    # Only import the legacy dataset if the SQLite database is still empty.
    if existing_reports == 0:
        for r in reports:
            rid = str(r.get("id") or uuid.uuid4())
            conn.execute("""
                INSERT OR IGNORE INTO reports
                (id,type,name,email,phone,site,location,date,items,description,reward,image_data,hidden_info,timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                rid, r.get("type", ""), r.get("name", ""), r.get("email", ""),
                r.get("phone", ""), r.get("site", ""), r.get("location", ""),
                r.get("date", ""), r.get("items", ""), r.get("description", ""),
                r.get("reward") or "", r.get("imageData"), int(bool(r.get("hiddenInfo"))),
                r.get("timestamp") or now_iso()
            ))
            imported_reports += 1

    for u in users:
        email = (u.get("email") or "").strip().lower()
        if not email or email == "admin@gmail.com":
            continue
        try:
            conn.execute("""
                INSERT INTO users (name,email,phone,password_hash,role,created_at)
                VALUES (?,?,?,?,?,?)
            """, (
                u.get("name") or email.split("@")[0],
                email,
                u.get("phone") or "",
                hash_password(u.get("password") or ""),
                "user",
                u.get("createdAt") or now_iso()
            ))
            imported_users += 1
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    return {"reports": imported_reports, "users": imported_users}


def seed_demo_reports():
    conn = db()
    count = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
    if count:
        conn.close()
        return
    site = "ICCT Colleges - Main Campus"
    locations = ['Main Lobby', 'Library', 'Computer Laboratory', 'Classroom Building', 'Hallway', 'Cafeteria', 'Student Lounge', 'Gymnasium', 'Parking Area', "Registrar's Office", 'School Grounds', 'Guidance Office', 'Faculty Area', 'Waiting Area', 'Stairway']
    items = ['Black Wallet', 'Smartphone', 'USB Flash Drive', 'Notebook', 'Wristwatch', 'Eyeglasses', 'Umbrella', 'Calculator', 'Helmet', 'Headphones', 'Wireless Mouse', 'Water Bottle', 'Student ID', 'Pen Case', 'Jacket', 'Tumbler', 'Textbook', 'Keychain', 'Laptop Charger', 'Personal Pouch', 'Power Bank', 'School Bag', 'Earphones', 'Folder', 'Ballpen']
    lost_names = ['Jericho Manalo', 'Maureen Villanueva', 'Renz Macapagal', 'Shaina Mercado', 'Jayson Soriano', 'Camille Padilla', 'Arvin Salcedo', 'Rica Domingo', 'Harold Evangelista', 'Trisha Alcantara', 'Nico Fernandez', 'Beatriz Mariano', 'Christian Pascual', 'Aira Valdez', 'Kenneth Bautista', 'Janelle Ramos', 'Marco Antonio Reyes', 'Clarisse Mendoza', 'Joshua Manansala', 'Elaine Rivera', 'Francisco Guevarra', 'Sheila Navarro', 'Gabriel Santiago', 'Mariel Aquino', 'Adrian Torres', 'Kristine Salonga', 'Nathaniel Flores', 'Karen Dizon', 'Eric Manalo', 'Diana Villarama', 'Carlo Mercado', 'Melissa Soriano', 'Anthony Macapagal', 'Christine Padilla', 'Jerome Salcedo', 'Carla Domingo', 'Vincent Evangelista', 'Joy Alcantara', 'Patrick Fernandez', 'Monica Mariano', 'Andrew Pascual', 'Grace Valdez', 'Robert Ramos', 'Leah Guevarra', 'Stephen Aquino', 'Andrea Salonga', 'Mark Bautista', 'Jennifer Dela Peña', 'Dennis Soriano', 'Angela Manansala', 'Kevin Macapagal', 'Catherine Villanueva', 'Joshua Mercado', 'Samantha Rivera', 'Daniel Manalo', 'Nicole Alcantara', 'Ryan Dizon', 'Ella Santiago', 'Jason Valdez', 'Mia Salcedo', 'John Mariano', 'Rhea Pascual', 'Luis Villarama', 'Trisha Dela Peña', 'Michael Guevarra', 'Bianca Villanueva', 'Rafael Villanueva', 'Hannah Macapagal', 'Gabriel Mariano', 'Sarah Domingo', 'Matthew Salonga', 'Jessa Manansala', 'Brian Torres', 'Alyssa Rivera', 'Carlo Macapagal', 'Isabelle Salcedo', 'Nathaniel Villanueva', 'Megan Aquino', 'Vincent Dela Peña', 'Lara Fernandez']
    found_names = ['Renato Manalo', 'Maricel Villanueva', 'Dennis Macapagal', 'Katrina Mercado', 'Jomar Soriano', 'Lourdes Padilla', 'Edwin Salcedo', 'Czarina Domingo', 'Rodrigo Evangelista', 'Marites Alcantara', 'Paolo Fernandez', 'Rowena Mariano', 'Edgar Pascual', 'Mylene Valdez', 'Rogelio Ramos', 'Arlene Salonga', 'Dennis Manansala', 'Marina Aquino', 'Rodel Castillo', 'Lorna Rivera', 'Ramon Guevarra', 'Nerissa Navarro', 'Gilbert Santiago', 'Rosario Aquino', 'Ernesto Torres', 'Marlene Salcedo', 'Roderick Flores', 'Gemma Dizon', 'Noel Manalo', 'Marissa Castillo', 'Reynaldo Dela Cruz', 'Corazon Santos', 'Nestor Reyes', 'Fe Garcia', 'Danilo Mendoza', 'Evelyn Flores', 'Rogelio Bautista', 'Nena Navarro', 'Armando Aquino', 'Carmela Castillo', 'Bong Manalo', 'Merlinda Santos', 'Renato Reyes', 'Rosita Garcia', 'Eduardo Mendoza', 'Luz Flores', 'Ruben Bautista', 'Celia Navarro', 'Ramil Aquino', 'Melanie Castillo', 'Rolando Dela Cruz', 'Elena Santos', 'Dennis Reyes', 'Lani Garcia', 'Marvin Mendoza', 'Roselle Flores', 'Santino Bautista', 'Mylene Navarro', 'Arturo Aquino', 'Lourdes Castillo', 'Edmundo Dela Cruz', 'Carmina Santos', 'Rogelio Reyes', 'Vilma Garcia', 'Alvin Mendoza', 'Charmaine Flores', 'Dennis Bautista', 'Elaine Navarro', 'Fernando Aquino', 'Gloria Castillo']
    rows = []
    for i, name in enumerate(lost_names):
        n = i + 1
        item = items[i % len(items)]
        location = locations[i % len(locations)]
        day = str((i % 30) + 1).zfill(2)
        rows.append((f"demo-lost-{n}", "Lost", name,
                     f"lost{n:03d}@lostnomore.com", f"0917{1000000+n}"[-11:],
                     site, location, f"2026-09-{day}", item,
                     f"{item} reported lost at the {location} of ICCT Colleges - Main Campus. Please contact the owner if found.",
                     "", None, 0, now_iso()))
    for i, name in enumerate(found_names):
        n = i + 1
        item = items[(i + 8) % len(items)]
        location = locations[(i + 4) % len(locations)]
        day = str((i % 30) + 1).zfill(2)
        rows.append((f"demo-found-{n}", "Found", name,
                     f"found{n:03d}@lostnomore.com", f"0917{2000000+n}"[-11:],
                     site, location, f"2026-09-{day}", item,
                     f"{item} found at the {location} of ICCT Colleges - Main Campus. The item is being reported for identification by its owner.",
                     "", None, 0, now_iso()))
    conn.executemany("""
        INSERT INTO reports
        (id,type,name,email,phone,site,location,date,items,description,reward,image_data,hidden_info,timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.commit()
    conn.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "LostNoMoreSQLite/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[LostNoMore] {self.address_string()} - {fmt % args}")

    def send_json(self, data, status=200, cookies=None):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        if cookies:
            for cookie in cookies:
                self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 25 * 1024 * 1024:
            raise ValueError("Request is too large.")
        body = self.rfile.read(length)
        return json.loads(body.decode("utf-8")) if body else {}

    def session_user(self):
        cookie = self.headers.get("Cookie", "")
        token = None
        for part in cookie.split(";"):
            part = part.strip()
            if part.startswith("lnm_session="):
                token = part.split("=", 1)[1]
                break
        return SESSIONS.get(token)

    def require_admin(self):
        user = self.session_user()
        if not user or not user.get("isAdmin"):
            self.send_json({"error": "Admin access required."}, 403)
            return None
        return user

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/bootstrap":
            conn = db()
            reports = [row_to_report(tuple(r)) for r in conn.execute(
                """SELECT id,type,name,email,phone,site,location,date,items,description,
                          reward,image_data,hidden_info,timestamp
                   FROM reports ORDER BY rowid DESC"""
            )]
            users = [row_to_user(tuple(r)) for r in conn.execute(
                "SELECT id,name,email,phone,role,created_at FROM users ORDER BY id"
            )]
            conn.close()
            self.send_json({
                "reports": reports,
                "users": users,
                "currentUser": self.session_user()
            })
            return

        if path == "/api/reports":
            conn = db()
            rows = conn.execute(
                """SELECT id,type,name,email,phone,site,location,date,items,description,
                          reward,image_data,hidden_info,timestamp
                   FROM reports ORDER BY rowid DESC"""
            ).fetchall()
            conn.close()
            self.send_json({"reports": [row_to_report(tuple(r)) for r in rows]})
            return

        if path == "/api/users":
            if not self.require_admin():
                return
            conn = db()
            rows = conn.execute(
                "SELECT id,name,email,phone,role,created_at FROM users ORDER BY id"
            ).fetchall()
            conn.close()
            self.send_json({"users": [row_to_user(tuple(r)) for r in rows]})
            return

        # Let SimpleHTTPRequestHandler serve index.html, CSS, JS, and images.
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.read_json()
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)
            return

        if path == "/api/migrate":
            result = import_legacy_data(data)
            self.send_json({"ok": True, "imported": result})
            return

        if path == "/api/login":
            email = (data.get("email") or "").strip().lower()
            password = data.get("password") or ""
            conn = db()
            row = conn.execute(
                """SELECT id,name,email,phone,role,created_at,password_hash
                   FROM users WHERE email = ?""", (email,)
            ).fetchone()
            conn.close()
            if not row or not secrets.compare_digest(row["password_hash"], hash_password(password)):
                self.send_json({"error": "Invalid email or password."}, 401)
                return
            user = row_to_user(tuple(row[:6]))
            token = uuid.uuid4().hex
            SESSIONS[token] = user
            cookie = f"lnm_session={token}; Path=/; HttpOnly; SameSite=Lax"
            self.send_json({"user": user}, 200, [cookie])
            return

        if path == "/api/logout":
            cookie = self.headers.get("Cookie", "")
            for part in cookie.split(";"):
                part = part.strip()
                if part.startswith("lnm_session="):
                    SESSIONS.pop(part.split("=", 1)[1], None)
            self.send_json({"ok": True}, 200, ["lnm_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"])
            return

        if path == "/api/users":
            name = (data.get("name") or "").strip()
            email = (data.get("email") or "").strip().lower()
            phone = (data.get("phone") or "").strip()
            password = data.get("password") or ""
            if not name or not email or not password:
                self.send_json({"error": "Name, email, and password are required."}, 400)
                return
            conn = db()
            try:
                conn.execute(
                    """INSERT INTO users (name,email,phone,password_hash,role,created_at)
                       VALUES (?,?,?,?, 'user', ?)""",
                    (name, email, phone, hash_password(password), now_iso())
                )
                conn.commit()
                row = conn.execute(
                    "SELECT id,name,email,phone,role,created_at FROM users WHERE email=?",
                    (email,)
                ).fetchone()
                conn.close()
                self.send_json({"user": row_to_user(tuple(row))}, 201)
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json({"error": "An account with this email already exists!"}, 409)
            return

        if path == "/api/reports":
            required = ["type", "name", "email", "phone", "items", "description"]
            if any(not str(data.get(k) or "").strip() for k in required):
                self.send_json({"error": "Missing required report fields."}, 400)
                return
            rid = str(data.get("id") or uuid.uuid4())
            conn = db()
            conn.execute("""
                INSERT INTO reports
                (id,type,name,email,phone,site,location,date,items,description,reward,image_data,hidden_info,timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                rid, data.get("type"), data.get("name"), data.get("email"),
                data.get("phone"), data.get("site") or "", data.get("location") or "",
                data.get("date") or "", data.get("items"), data.get("description") or "",
                data.get("reward") or "", data.get("imageData"), int(bool(data.get("hiddenInfo"))),
                data.get("timestamp") or now_iso()
            ))
            conn.commit()
            conn.close()
            self.send_json({"ok": True, "id": rid}, 201)
            return

        # Admin mutation endpoints
        if path.startswith("/api/reports/") and path.endswith("/toggle-hidden"):
            if not self.require_admin():
                return
            rid = path.split("/")[3]
            conn = db()
            conn.execute(
                "UPDATE reports SET hidden_info = CASE hidden_info WHEN 0 THEN 1 ELSE 0 END WHERE id=?",
                (rid,)
            )
            conn.commit()
            conn.close()
            self.send_json({"ok": True})
            return

        if path == "/api/admin/verify":
            user = self.require_admin()
            if not user:
                return
            conn = db()
            row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
            conn.close()
            if not row or not secrets.compare_digest(row["password_hash"], hash_password(data.get("password") or "")):
                self.send_json({"error": "Invalid admin password."}, 401)
            else:
                self.send_json({"ok": True})
            return

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/reports/"):
            self.send_json({"error": "Not found."}, 404)
            return
        if not self.require_admin():
            return
        rid = path.split("/")[3]
        try:
            data = self.read_json()
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        conn = db()
        conn.execute("""
            UPDATE reports SET
              type=?, name=?, email=?, phone=?, items=?, description=?,
              site=?, location=?, date=?, reward=?, image_data=?
            WHERE id=?
        """, (
            data.get("type"), data.get("name"), data.get("email"), data.get("phone"),
            data.get("items"), data.get("description"), data.get("site") or "",
            data.get("location") or "", data.get("date") or "", data.get("reward") or "",
            data.get("imageData"), rid
        ))
        conn.commit()
        changed = conn.total_changes
        conn.close()
        self.send_json({"ok": changed > 0}, 200 if changed > 0 else 404)

    def do_DELETE(self):
        path = urlparse(self.path).path

        if path.startswith("/api/reports/"):
            if not self.require_admin():
                return
            rid = path.split("/")[3]
            conn = db()
            cur = conn.execute("DELETE FROM reports WHERE id=?", (rid,))
            conn.commit()
            changed = cur.rowcount
            conn.close()
            self.send_json({"ok": changed > 0}, 200 if changed > 0 else 404)
            return

        if path == "/api/users":
            if not self.require_admin():
                return
            query = parse_qs(urlparse(self.path).query)
            email = (query.get("email") or [""])[0].strip().lower()
            if not email:
                self.send_json({"error": "Email is required."}, 400)
                return
            if email == "admin@gmail.com":
                self.send_json({"error": "The main administrator account cannot be deleted."}, 400)
                return
            conn = db()
            cur = conn.execute("DELETE FROM users WHERE email=?", (email,))
            conn.execute("DELETE FROM reports WHERE email=?", (email,))
            conn.commit()
            changed = cur.rowcount
            conn.close()
            self.send_json({"ok": changed > 0}, 200 if changed > 0 else 404)
            return

        self.send_json({"error": "Not found."}, 404)


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    init_db()
    seed_demo_reports()
    os.chdir(APP_DIR)
    with ReusableThreadingTCPServer((HOST, PORT), Handler) as server:
        url = f"http://{HOST}:{PORT}/index.html"
        print("=" * 64)
        print("LostNoMore - SQLite Edition is running!")
        print(f"SQLite database: {DB_PATH}")
        print(f"Open: {url}")
        print("Press CTRL+C in this window to stop the server.")
        print("=" * 64)
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nLostNoMore stopped.")


if __name__ == "__main__":
    main()
