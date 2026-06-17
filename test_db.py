# -*- coding: utf-8 -*-
import os, tempfile
import arabic_reshaper
from bidi.algorithm import get_display
from database import Database, GOVERNORATES

def ar(t):
    if not t: return ""
    return get_display(arabic_reshaper.reshape(str(t)))

path = os.path.join(tempfile.mkdtemp(), "t.db")
db = Database(path)

# 1) المحافظات مزروعة و = 15
govs = db.get_governorates()
assert len(govs) == 15, len(govs)
names = [g["name"] for g in govs]
for excluded in ["أربيل", "السليمانية", "دهوك", "حلبجة"]:
    assert excluded not in names
print("OK المحافظات:", len(govs))

# 2) إضافة مؤسسة
baghdad = [g["id"] for g in govs if g["name"] == "بغداد"][0]
inst_id = db.add_institution("مديرية الأحوال المدنية", "الكرخ", baghdad)
basra = [g["id"] for g in govs if g["name"] == "البصرة"][0]
db.add_institution("مديرية المرور", "قضاء البصرة", basra)
insts = db.get_institutions()
assert len(insts) == 2, len(insts)
insts_baghdad = db.get_institutions(baghdad)
assert len(insts_baghdad) == 1
print("OK المؤسسات:", [i["name"] for i in insts])

# 3) إضافة أفراد
db.add_individual("محمد علي حسين", "07901234567", "بغداد - المنصور", inst_id)
db.add_individual("أحمد كريم", "07700000000", "البصرة - العشار", inst_id)
ppl = db.get_individuals(inst_id)
assert len(ppl) == 2
print("OK الأفراد:", [p["name"] for p in ppl])

# 4) البحث
res = db.search("محمد")
assert len(res["individuals"]) == 1
res2 = db.search("المرور")
assert len(res2["institutions"]) == 1
res3 = db.search("07700000000")
assert len(res3["individuals"]) == 1
print("OK البحث: بالاسم/الهاتف/المؤسسة")

# 5) التحقق من قيود المفتاح الأجنبي والحذف المتسلسل
db.delete_institution(inst_id)
assert len(db.get_individuals()) == 0  # تم حذف الأفراد التابعين تلقائياً
print("OK الحذف المتسلسل")

# 6) دالة العرض العربي تعمل
shaped = ar("مديرية الأحوال المدنية")
assert shaped and shaped != "مديرية الأحوال المدنية"
print("OK العرض العربي:", repr(ar("اختبار 123")))

print("\n>>> كل اختبارات قاعدة البيانات نجحت <<<")
