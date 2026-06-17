# -*- coding: utf-8 -*-
"""
طبقة قاعدة البيانات لتطبيق "معرفو المؤسسات الحكومية".
هذا الملف لا يستورد Kivy/KivyMD إطلاقاً حتى يبقى قابلاً للاختبار بسهولة.

الهيكلية:
    المحافظة (governorate)
        └── المؤسسة (institution)  -> الاسم + القضاء التابع له
                └── الفرد (individual) -> الاسم + الهاتف + عنوان السكن
"""

import sqlite3

# محافظات العراق عدا إقليم كردستان (أربيل، السليمانية، دهوك، وحلبجة)
GOVERNORATES = [
    "بغداد",
    "البصرة",
    "نينوى",
    "ذي قار",
    "الأنبار",
    "ديالى",
    "كركوك",
    "النجف",
    "كربلاء",
    "بابل",
    "واسط",
    "صلاح الدين",
    "القادسية",
    "ميسان",
    "المثنى",
]

# مؤسسات تُزرع تلقائياً عند أول تشغيل (اختياري).
# الصيغة: (اسم المحافظة, القضاء, اسم المؤسسة)
# اتركها فارغة [] إن لم ترغب بأي بيانات أولية.
SEED_INSTITUTIONS = [
    # ("بغداد", "الكرخ", "مديرية الأحوال المدنية"),
    # ("البصرة", "قضاء البصرة", "مديرية المرور العامة"),
]


class Database:
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self.seed_governorates()
        self.seed_institutions()

    # ---------------------------------------------------------------- إنشاء
    def _create_tables(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS governorates (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS institutions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                district       TEXT,                 -- القضاء التابع له
                governorate_id INTEGER NOT NULL,
                FOREIGN KEY (governorate_id)
                    REFERENCES governorates (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS individuals (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                phone          TEXT,
                address        TEXT,                 -- عنوان السكن
                institution_id INTEGER NOT NULL,
                FOREIGN KEY (institution_id)
                    REFERENCES institutions (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_inst_gov  ON institutions (governorate_id);
            CREATE INDEX IF NOT EXISTS idx_indiv_ins ON individuals  (institution_id);
            """
        )
        self.conn.commit()

    # ---------------------------------------------------------------- بذور
    def seed_governorates(self):
        cur = self.conn.cursor()
        for name in GOVERNORATES:
            cur.execute(
                "INSERT OR IGNORE INTO governorates (name) VALUES (?)", (name,)
            )
        self.conn.commit()

    def seed_institutions(self):
        if not SEED_INSTITUTIONS:
            return
        # لا نزرع إلا إذا كان الجدول فارغاً (حتى لا نكرر عند كل تشغيل)
        if self.conn.execute("SELECT COUNT(*) FROM institutions").fetchone()[0] > 0:
            return
        for gov_name, district, inst_name in SEED_INSTITUTIONS:
            gov = self.conn.execute(
                "SELECT id FROM governorates WHERE name = ?", (gov_name,)
            ).fetchone()
            if gov:
                self.add_institution(inst_name, district, gov["id"])

    # ----------------------------------------------------------- المحافظات
    def get_governorates(self):
        return self.conn.execute(
            "SELECT id, name FROM governorates ORDER BY id"
        ).fetchall()

    # ----------------------------------------------------------- المؤسسات
    def add_institution(self, name, district, governorate_id):
        name = (name or "").strip()
        if not name:
            raise ValueError("اسم المؤسسة مطلوب")
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO institutions (name, district, governorate_id) "
            "VALUES (?, ?, ?)",
            (name, (district or "").strip(), governorate_id),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_institution(self, inst_id, name, district, governorate_id):
        self.conn.execute(
            "UPDATE institutions SET name = ?, district = ?, governorate_id = ? "
            "WHERE id = ?",
            ((name or "").strip(), (district or "").strip(), governorate_id, inst_id),
        )
        self.conn.commit()

    def delete_institution(self, inst_id):
        self.conn.execute("DELETE FROM institutions WHERE id = ?", (inst_id,))
        self.conn.commit()

    def get_institutions(self, governorate_id=None):
        sql = (
            "SELECT i.id, i.name, i.district, i.governorate_id, g.name AS gov_name "
            "FROM institutions i JOIN governorates g ON g.id = i.governorate_id "
        )
        params = ()
        if governorate_id is not None:
            sql += "WHERE i.governorate_id = ? "
            params = (governorate_id,)
        sql += "ORDER BY g.name, i.name"
        return self.conn.execute(sql, params).fetchall()

    # ------------------------------------------------------------- الأفراد
    def add_individual(self, name, phone, address, institution_id):
        name = (name or "").strip()
        if not name:
            raise ValueError("اسم الفرد مطلوب")
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO individuals (name, phone, address, institution_id) "
            "VALUES (?, ?, ?, ?)",
            (name, (phone or "").strip(), (address or "").strip(), institution_id),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_individual(self, ind_id, name, phone, address, institution_id):
        self.conn.execute(
            "UPDATE individuals SET name = ?, phone = ?, address = ?, "
            "institution_id = ? WHERE id = ?",
            (
                (name or "").strip(),
                (phone or "").strip(),
                (address or "").strip(),
                institution_id,
                ind_id,
            ),
        )
        self.conn.commit()

    def delete_individual(self, ind_id):
        self.conn.execute("DELETE FROM individuals WHERE id = ?", (ind_id,))
        self.conn.commit()

    def get_individuals(self, institution_id=None):
        sql = (
            "SELECT p.id, p.name, p.phone, p.address, p.institution_id, "
            "i.name AS inst_name, i.district, g.name AS gov_name "
            "FROM individuals p "
            "JOIN institutions i ON i.id = p.institution_id "
            "JOIN governorates g ON g.id = i.governorate_id "
        )
        params = ()
        if institution_id is not None:
            sql += "WHERE p.institution_id = ? "
            params = (institution_id,)
        sql += "ORDER BY g.name, i.name, p.name"
        return self.conn.execute(sql, params).fetchall()

    # -------------------------------------------------------------- البحث
    def search(self, term):
        """بحث شامل في الأفراد (الاسم/الهاتف/العنوان) والمؤسسات (الاسم/القضاء)."""
        term = (term or "").strip()
        if not term:
            return {"individuals": [], "institutions": []}
        like = f"%{term}%"

        individuals = self.conn.execute(
            "SELECT p.id, p.name, p.phone, p.address, p.institution_id, "
            "i.name AS inst_name, i.district, g.name AS gov_name "
            "FROM individuals p "
            "JOIN institutions i ON i.id = p.institution_id "
            "JOIN governorates g ON g.id = i.governorate_id "
            "WHERE p.name LIKE ? OR p.phone LIKE ? OR p.address LIKE ? "
            "ORDER BY p.name",
            (like, like, like),
        ).fetchall()

        institutions = self.conn.execute(
            "SELECT i.id, i.name, i.district, i.governorate_id, g.name AS gov_name "
            "FROM institutions i JOIN governorates g ON g.id = i.governorate_id "
            "WHERE i.name LIKE ? OR i.district LIKE ? "
            "ORDER BY i.name",
            (like, like),
        ).fetchall()

        return {"individuals": individuals, "institutions": institutions}

    def close(self):
        self.conn.close()
