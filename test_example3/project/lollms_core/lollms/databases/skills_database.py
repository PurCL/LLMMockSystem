import sqlite3

class SkillsLibrary:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_table()

        
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._initialize_db()

    def _initialize_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_library (
                id INTEGER PRIMARY KEY,
                version INTEGER,
                category TEXT,
                title TEXT,
                content TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_info (
                version INTEGER
            )
        """)
        self.cursor.execute("SELECT version FROM db_info")
        version = self.cursor.fetchone()
        if version is None:
            self.cursor.execute("INSERT INTO db_info (version) VALUES (1)")
            self.conn.commit()
        else:
            self._migrate_db(version[0])

    def _migrate_db(self, version):
        # Perform migrations based on the current version
        # For example, if the current version is 1 and the latest version is 2:
        if version < 2:
            self.cursor.execute("ALTER TABLE skills_library ADD COLUMN new_column TEXT")
            self.cursor.execute("UPDATE db_info SET version = 2")
            self.conn.commit()

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_library (
                id INTEGER PRIMARY KEY,
                version INTEGER,
                category TEXT,
                title TEXT,
                content TEXT
            )
        """)
        self.conn.commit()

    def add_entry(self, version, category, title, content):
        self.cursor.execute("""
            INSERT INTO skills_library (version, category, title, content) 
            VALUES (?, ?, ?, ?)
        """, (version, category, title, content))
        self.conn.commit()

    def list_entries(self):
        self.cursor.execute("SELECT * FROM skills_library")
        return self.cursor.fetchall()

    def query_entry(self, text):
        self.cursor.execute("""
            SELECT * FROM skills_library 
            WHERE category LIKE ? OR title LIKE ? OR content LIKE ?
        """, (f'%{text}%', f'%{text}%', f'%{text}%'))
        return self.cursor.fetchall()

    def remove_entry(self, id):
        self.cursor.execute("DELETE FROM skills_library WHERE id = ?", (id,))
        self.conn.commit()

    def export_entries(self, file_path):
        with open(file_path, 'w') as f:
            for entry in self.list_entries():
                f.write(f'{entry}\n')

    def import_entries(self, file_path):
        with open(file_path, 'r') as f:
            for line in f:
                entry = line.strip().split(',')
                self.add_entry(*entry)

    def fuse_with_another_db(self, other_db_path):
        other_conn = sqlite3.connect(other_db_path)
        other_cursor = other_conn.cursor()
        other_cursor.execute("SELECT * FROM skills_library")
        for row in other_cursor.fetchall():
            self.add_entry(*row[1:])  # skip the id column
