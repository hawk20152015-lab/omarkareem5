[app]
title = معرفو المؤسسات
package.name = marifin
package.domain = org.iq.marifin
source.dir = .
source.include_exts = py,png,jpg,ttf,kv,db
version = 1.0

# المتطلبات — انتبه: نستخدم pybidi (وليس python-bidi) لأنها تُبنى على أندرويد
requirements = python3,kivy==2.3.0,kivymd==1.1.1,sqlite3,arabic-reshaper,pybidi

orientation = portrait
fullscreen = 0

# ملفات الخطوط تُحزَم تلقائياً عبر source.include_exts=ttf أعلاه

# الصلاحيات (التخزين الداخلي يكفي)
android.permissions =

# معماريات المعالج
android.archs = arm64-v8a, armeabi-v7a

# مستويات الـ API
android.api = 34
android.minapi = 21

# قبول تراخيص SDK تلقائياً (مفيد للبناء بلا تدخّل)
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
