"""
Database schema for storing job descriptions and generated resumes
"""
import sqlite3
from pathlib import Path
from datetime import datetime

class Database:
    def __init__(self, db_path="resume_generator.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Job descriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_descriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                job_title TEXT,
                job_description TEXT NOT NULL,
                job_url TEXT,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_name, job_description)
            )
        """)

        # Generated resumes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_description_id INTEGER NOT NULL,
                resume_content TEXT NOT NULL,
                ats_score INTEGER,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id),
                UNIQUE(job_description_id)
            )
        """)

        # Company research cache (from Perplexity)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_research (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT UNIQUE NOT NULL,
                research_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Generated cover letters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_cover_letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_description_id INTEGER NOT NULL,
                resume_id INTEGER,
                cover_letter_content TEXT NOT NULL,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id),
                FOREIGN KEY (resume_id) REFERENCES generated_resumes(id),
                UNIQUE(job_description_id)
            )
        """)

        conn.commit()
        conn.close()

    def insert_job_description(self, company_name, job_description, job_title=None, job_url=None, keywords=None):
        """Insert or get existing job description"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO job_descriptions (company_name, job_title, job_description, job_url, keywords)
                VALUES (?, ?, ?, ?, ?)
            """, (company_name, job_title, job_description, job_url, keywords))
            conn.commit()
            job_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Job description already exists
            cursor.execute("""
                SELECT id FROM job_descriptions
                WHERE company_name = ? AND job_description = ?
            """, (company_name, job_description))
            job_id = cursor.fetchone()[0]

        conn.close()
        return job_id

    def check_resume_exists(self, job_description_id):
        """Check if resume already generated for this job"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, file_path, created_at FROM generated_resumes
            WHERE job_description_id = ?
        """, (job_description_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "id": result[0],
                "file_path": result[1],
                "created_at": result[2]
            }
        return None

    def insert_generated_resume(self, job_description_id, resume_content, file_path, ats_score=None):
        """Insert generated resume"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO generated_resumes (job_description_id, resume_content, file_path, ats_score)
                VALUES (?, ?, ?, ?)
            """, (job_description_id, resume_content, file_path, ats_score))
            conn.commit()
            resume_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Resume already exists, update it
            cursor.execute("""
                UPDATE generated_resumes
                SET resume_content = ?, file_path = ?, ats_score = ?
                WHERE job_description_id = ?
            """, (resume_content, file_path, ats_score, job_description_id))
            conn.commit()
            cursor.execute("""
                SELECT id FROM generated_resumes WHERE job_description_id = ?
            """, (job_description_id,))
            resume_id = cursor.fetchone()[0]

        conn.close()
        return resume_id

    def get_company_research(self, company_name):
        """Get cached company research"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT research_data FROM company_research
            WHERE company_name = ?
        """, (company_name,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def save_company_research(self, company_name, research_data):
        """Save company research to cache"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO company_research (company_name, research_data)
            VALUES (?, ?)
        """, (company_name, research_data))

        conn.commit()
        conn.close()

    def get_all_resumes(self):
        """Get all generated resumes with job info"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                r.id,
                j.company_name,
                j.job_title,
                r.file_path,
                r.ats_score,
                r.created_at
            FROM generated_resumes r
            JOIN job_descriptions j ON r.job_description_id = j.id
            ORDER BY r.created_at DESC
        """)

        results = cursor.fetchall()
        conn.close()

        return [{
            "id": row[0],
            "company_name": row[1],
            "job_title": row[2],
            "file_path": row[3],
            "ats_score": row[4],
            "created_at": row[5]
        } for row in results]

    def check_cover_letter_exists(self, job_description_id):
        """Check if cover letter already generated for this job"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, file_path, created_at FROM generated_cover_letters
            WHERE job_description_id = ?
        """, (job_description_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                "id": result[0],
                "file_path": result[1],
                "created_at": result[2]
            }
        return None

    def insert_generated_cover_letter(self, job_description_id, cover_letter_content, file_path, resume_id=None):
        """Insert generated cover letter"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO generated_cover_letters (job_description_id, resume_id, cover_letter_content, file_path)
                VALUES (?, ?, ?, ?)
            """, (job_description_id, resume_id, cover_letter_content, file_path))
            conn.commit()
            cover_letter_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Cover letter already exists, update it
            cursor.execute("""
                UPDATE generated_cover_letters
                SET cover_letter_content = ?, file_path = ?, resume_id = ?
                WHERE job_description_id = ?
            """, (cover_letter_content, file_path, resume_id, job_description_id))
            conn.commit()
            cursor.execute("""
                SELECT id FROM generated_cover_letters WHERE job_description_id = ?
            """, (job_description_id,))
            cover_letter_id = cursor.fetchone()[0]

        conn.close()
        return cover_letter_id
