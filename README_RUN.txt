LostNoMore - Python + SQLite Edition
====================================

This version uses a real SQLite database instead of browser localStorage for
persistent application data.

Database file:
    lostnomore.db

SQLite tables:
    users
    reports

The Python launcher also provides the small HTTP API used by the JavaScript
frontend. No Flask, pip package, or external dependency is required.

VS Code / Windows
-----------------
1. Extract the ZIP.
2. Open the extracted "LostNoMore_Python" folder in VS Code.
3. Open Terminal -> New Terminal.
4. Run:
       python run.py
   or:
       py run.py
5. Your browser opens:
       http://127.0.0.1:8000/index.html
6. Keep the terminal open while using the system.
7. Press Ctrl+C to stop the server.

Default administrator
---------------------
Email:    admin@gmail.com
Password: admin123

The administrator account is created in SQLite automatically on first run.

Data migration
--------------
If the previous LostNoMore version has reports/users in browser localStorage,
the SQLite edition performs a one-time migration when it starts. After a
successful migration, those old localStorage records are removed.

Notes
-----
- Reports, users, edits, deletes, privacy flags, and login authentication are
  handled by the Python SQLite backend.
- Uploaded report images are stored in the SQLite reports table as image data.
- The browser does not store the application's reports/users in localStorage.
- The SQLite database is created automatically beside run.py.
