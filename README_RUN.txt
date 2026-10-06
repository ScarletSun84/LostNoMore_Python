LOSTNOMORE - CUSTOMTKINTER DESKTOP

Run:
  python main.py

The application automatically checks for Tkinter, Pillow, and ReportLab.
If any are missing, it installs them from requirements.txt using the same Python interpreter.

You can also double-click run_desktop.bat.
Internet access is required the first time missing packages are installed.


6. Tools and Technologies

+----------------------------+------------------------------------------------------------+
| Category                   | Technology                                                  |
+----------------------------+------------------------------------------------------------+
| Programming Language      | Python                                                     |
| GUI Framework             | Tkinter                                              |
| Database                  | SQLite                                                     |
| Database Connector        | sqlite3                                                    |
| IDE / Editor              | Visual Studio Code                                        |
| Version Control            | Git and GitHub (if used for the project)                  |
| Other Libraries            | Pillow for image handling; ReportLab for PDF reports      |
+----------------------------+------------------------------------------------------------+

Note: The LostNoMore application uses SQLite only; MySQL is not part of the current implementation.
CSV export is not listed because the current application does not use a CSV library/export feature.

ADMIN ACCOUNT
-------------
The included database contains one administrator account for system administration.

Email: admin@lostnomore.com
Password: Admin@2026!

The credentials are not displayed on the application's login screen.

REPORTS FIX: All Reports now uses a reliable Tkinter Treeview with vertical scrolling, search/filter, SHOW ALL, and double-click details.
