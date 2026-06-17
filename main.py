# -*- coding: utf-8 -*-
"""
معرفو المؤسسات الحكومية — تطبيق هاتف (Kivy + KivyMD + SQLite)
دعم عربي كامل (RTL + تشكيل الحروف) — أيقونات في الشريط العلوي بدل الأزرار العائمة.

الهيكلية:  المحافظة ← المؤسسة (الاسم + القضاء) ← الفرد (الاسم + الهاتف + العنوان)

ملاحظة الخطوط: ضع ملف خط عربي داخل مجلد fonts/ (مثل Amiri-Regular.ttf أو
Cairo-Regular.ttf). بدونه ستظهر الحروف العربية غير متصلة.
"""

import os

from kivy.lang import Builder
from kivy.core.text import LabelBase
from kivy.utils import platform
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout

import arabic_reshaper
try:
    # سطح المكتب: حزمة python-bidi
    from bidi.algorithm import get_display
except ImportError:
    # أندرويد: نستخدم pybidi (تُبنى بنجاح عبر buildozer)
    from pybidi.algorithm import get_display

from database import Database

try:
    from kivymd.uix.snackbar import Snackbar
except Exception:  # pragma: no cover
    Snackbar = None


# ======================================================================
#  أدوات اللغة العربية
# ======================================================================
# اجعلها False فقط إذا ظهر النص معكوساً مرتين (مشكلة معروفة على ويندوز
# مع بعض إصدارات SDL). على أندرويد اتركها True.
USE_BIDI = True


def ar(text):
    """يُرجع نصاً عربياً مُشكَّلاً جاهزاً للعرض (لا يُستخدم للتخزين)."""
    if text is None:
        return ""
    text = str(text)
    if not text.strip():
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped) if USE_BIDI else reshaped


# تسجيل خط عربي بمسار مطلق (يعمل على أندرويد وأي مجلد عمل).
# نسجّله مرة باسم "Arabic" ومرة نتجاوز به أنماط KivyMD لاحقاً.
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_HERE, "fonts")

# (الملف العادي، الملف العريض)
# Amiri أولاً: يغطي أشكال العرض العربية كاملة المطلوبة لمكتبة arabic_reshaper.
# تجنّب الخطوط الحديثة (Tajawal/Cairo) التي تعتمد OpenType وتنقصها بعض الأشكال.
_FONT_CANDIDATES = [
    ("Amiri-Regular.ttf", "Amiri-Bold.ttf"),
    ("NotoNaskhArabic-Regular.ttf", None),
    ("Scheherazade-Regular.ttf", None),
    ("Lateef-Regular.ttf", None),
]

ARABIC_FONT = "Roboto"
for _reg, _bold in _FONT_CANDIDATES:
    _rp = os.path.join(_FONT_DIR, _reg)
    if os.path.exists(_rp):
        _bp = os.path.join(_FONT_DIR, _bold) if _bold else None
        if not (_bp and os.path.exists(_bp)):
            _bp = _rp
        LabelBase.register(name="Arabic", fn_regular=_rp, fn_bold=_bp)
        ARABIC_FONT = "Arabic"
        break


# ======================================================================
#  حقل إدخال عربي
# ======================================================================
def _fix_field_fonts(field, *a):
    """يضبط خط العناصر الداخلية للحقل (التلميح/المساعدة/العداد) إلى الخط العربي."""
    for attr in ("_hint_text_label", "_helper_text_label", "_max_length_label"):
        lbl = getattr(field, attr, None)
        if lbl is not None:
            try:
                lbl.font_name = ARABIC_FONT
            except Exception:
                pass


class NumberInput(MDTextField):
    """حقل رقمي (الهاتف): يبقى من اليسار، لكن تلميحه بالخط العربي."""

    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", ARABIC_FONT)
        super().__init__(**kwargs)
        Clock.schedule_once(lambda dt: _fix_field_fonts(self), 0)
        self.bind(hint_text=lambda *a: _fix_field_fonts(self))


class ArabicInput(MDTextField):
    """
    حقل نصي عربي يُشكّل الحروف ويصحّح الاتجاه مباشرةً أثناء الكتابة:
      - raw_text يحتفظ بالنص الحقيقي (ترتيب منطقي) للتخزين والبحث.
      - الحقل يعرض دائماً النسخة المُشكَّلة المصحّحة الاتجاه عبر ar().
      - get_raw() يُرجع النص الحقيقي في أي لحظة (لا يعتمد على مغادرة الحقل).
    """

    raw_text = StringProperty("")

    def __init__(self, **kwargs):
        kwargs.setdefault("font_name", ARABIC_FONT)
        kwargs.setdefault("halign", "right")
        super().__init__(**kwargs)
        Clock.schedule_once(lambda dt: _fix_field_fonts(self), 0)
        self.bind(hint_text=lambda *a: _fix_field_fonts(self))

    def insert_text(self, substring, from_undo=False):
        # نضيف الحرف للنص الخام ثم نعرض المُشكَّل (لا ننادي super حتى لا يُدرج الخام)
        if from_undo or self.readonly:
            return super().insert_text(substring, from_undo=from_undo)
        self.raw_text += substring
        self._render()
        return None

    def do_backspace(self, from_undo=False, mode="bkspc"):
        if self.readonly:
            return super().do_backspace(from_undo=from_undo, mode=mode)
        if self.raw_text:
            self.raw_text = self.raw_text[:-1]
            self._render()
        return None

    def _render(self):
        shaped = ar(self.raw_text)
        if self.text != shaped:
            self.text = shaped
        Clock.schedule_once(self._cursor_to_end, 0)

    def _cursor_to_end(self, *a):
        try:
            self.cursor = (len(self.text), 0)
        except Exception:
            pass

    def get_raw(self):
        return self.raw_text

    def set_value(self, raw):
        self.raw_text = raw or ""
        self._render()

    def clear(self):
        self.raw_text = ""
        self.text = ""


# ======================================================================
#  بطاقة عنصر في القائمة (مؤسسة / فرد) — تحكم كامل بالخط والاتجاه
# ======================================================================
class RecordCard(MDCard):
    title = StringProperty("")
    subtitle = StringProperty("")
    rec_id = NumericProperty(0)
    tap_action = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def trigger(self, *a):
        if self.tap_action:
            self.tap_action(self.rec_id)


# ======================================================================
#  الشاشات
# ======================================================================
class HomeScreen(MDScreen):
    pass


class InstitutionsScreen(MDScreen):
    pass


class IndividualsScreen(MDScreen):
    pass


class SearchScreen(MDScreen):
    pass


class AddInstitutionScreen(MDScreen):
    pass


class AddIndividualScreen(MDScreen):
    pass


class BrowseGovScreen(MDScreen):
    pass


class BrowseInstScreen(MDScreen):
    pass


class BrowseIndivScreen(MDScreen):
    pass


# ======================================================================
#  واجهة KV
# ======================================================================
KV = '''

<RecordCard>:
    orientation: "vertical"
    size_hint_y: None
    height: self.minimum_height
    padding: dp(14), dp(10)
    spacing: dp(2)
    radius: [12]
    elevation: 1
    md_bg_color: app.theme_cls.bg_light
    ripple_behavior: True
    on_release: root.trigger()

    MDLabel:
        text: app.ar(root.title)
        font_name: app.arabic_font
        halign: "right"
        bold: True
        font_style: "Subtitle1"
        adaptive_height: True

    MDLabel:
        text: app.ar(root.subtitle)
        font_name: app.arabic_font
        halign: "right"
        theme_text_color: "Secondary"
        font_style: "Caption"
        adaptive_height: True


# ---------------------------------------------------------------- الرئيسية
<HomeScreen>:
    name: "home"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: app.ar("معرفو المؤسسات الحكومية")
            font_name: app.arabic_font
            elevation: 2
            right_action_items: [["magnify", lambda x: app.go("search")]]
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(20)
            spacing: dp(16)
            adaptive_height: True
            pos_hint: {"top": 1}

            MDCard:
                size_hint_y: None
                height: dp(110)
                radius: [16]
                elevation: 2
                ripple_behavior: True
                on_release: app.go("institutions")
                MDBoxLayout:
                    padding: dp(18)
                    MDLabel:
                        text: app.ar("المؤسسات")
                        font_name: app.arabic_font
                        halign: "right"
                        font_style: "H6"
                    MDIcon:
                        icon: "office-building"
                        size_hint_x: None
                        width: dp(48)
                        font_size: dp(36)

            MDCard:
                size_hint_y: None
                height: dp(110)
                radius: [16]
                elevation: 2
                ripple_behavior: True
                on_release: app.go("individuals")
                MDBoxLayout:
                    padding: dp(18)
                    MDLabel:
                        text: app.ar("الأفراد")
                        font_name: app.arabic_font
                        halign: "right"
                        font_style: "H6"
                    MDIcon:
                        icon: "account-multiple"
                        size_hint_x: None
                        width: dp(48)
                        font_size: dp(36)

            MDCard:
                size_hint_y: None
                height: dp(110)
                radius: [16]
                elevation: 2
                ripple_behavior: True
                on_release: app.go("search")
                MDBoxLayout:
                    padding: dp(18)
                    MDLabel:
                        text: app.ar("بحث وعرض")
                        font_name: app.arabic_font
                        halign: "right"
                        font_style: "H6"
                    MDIcon:
                        icon: "magnify"
                        size_hint_x: None
                        width: dp(48)
                        font_size: dp(36)

            MDCard:
                size_hint_y: None
                height: dp(110)
                radius: [16]
                elevation: 2
                ripple_behavior: True
                on_release: app.go("browse_gov")
                MDBoxLayout:
                    padding: dp(18)
                    MDLabel:
                        text: app.ar("المحافظات")
                        font_name: app.arabic_font
                        halign: "right"
                        font_style: "H6"
                    MDIcon:
                        icon: "map-marker-multiple"
                        size_hint_x: None
                        width: dp(48)
                        font_size: dp(36)
        Widget:


# ---------------------------------------------------------------- المؤسسات
<InstitutionsScreen>:
    name: "institutions"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: app.ar("المؤسسات")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("home")]]
            right_action_items: [["plus", lambda x: app.open_add_institution()]]
        ScrollView:
            MDBoxLayout:
                id: inst_list
                orientation: "vertical"
                padding: dp(12)
                spacing: dp(10)
                adaptive_height: True


# ----------------------------------------------------------------- الأفراد
<IndividualsScreen>:
    name: "individuals"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: app.ar("الأفراد")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("home")]]
            right_action_items: [["plus", lambda x: app.open_add_individual()]]
        ScrollView:
            MDBoxLayout:
                id: indiv_list
                orientation: "vertical"
                padding: dp(12)
                spacing: dp(10)
                adaptive_height: True


# ------------------------------------------------------------------- البحث
<SearchScreen>:
    name: "search"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: app.ar("بحث وعرض")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("home")]]
        MDBoxLayout:
            size_hint_y: None
            height: dp(72)
            padding: dp(12), dp(8)
            ArabicInput:
                id: search_field
                hint_text: app.ar("اكتب اسماً أو هاتفاً أو مؤسسة...")
                mode: "rectangle"
                on_text: app.do_search(self.get_raw())
        ScrollView:
            MDBoxLayout:
                id: search_results
                orientation: "vertical"
                padding: dp(12)
                spacing: dp(10)
                adaptive_height: True


# ------------------------------------------------------- إضافة مؤسسة
<AddInstitutionScreen>:
    name: "add_institution"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: app.ar("إضافة / تعديل مؤسسة")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("institutions")]]
            right_action_items: [["content-save", lambda x: app.save_institution()]]
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(20)
            spacing: dp(18)
            adaptive_height: True
            pos_hint: {"top": 1}

            ArabicInput:
                id: gov_field
                hint_text: app.ar("المحافظة")
                mode: "rectangle"
                readonly: True
                on_focus: if self.focus: app.open_gov_menu(self)

            ArabicInput:
                id: district_field
                hint_text: app.ar("القضاء التابع له")
                mode: "rectangle"

            ArabicInput:
                id: inst_name_field
                hint_text: app.ar("اسم المؤسسة")
                mode: "rectangle"
        Widget:


# -------------------------------------------------------- إضافة فرد
<AddIndividualScreen>:
    name: "add_individual"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: app.ar("إضافة / تعديل فرد")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("individuals")]]
            right_action_items: [["content-save", lambda x: app.save_individual()]]
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(20)
                spacing: dp(18)
                adaptive_height: True

                ArabicInput:
                    id: ind_gov_field
                    hint_text: app.ar("المحافظة")
                    mode: "rectangle"
                    readonly: True
                    on_focus: if self.focus: app.open_ind_gov_menu(self)

                ArabicInput:
                    id: ind_inst_field
                    hint_text: app.ar("المؤسسة")
                    mode: "rectangle"
                    readonly: True
                    on_focus: if self.focus: app.open_ind_inst_menu(self)

                ArabicInput:
                    id: ind_name_field
                    hint_text: app.ar("اسم الفرد")
                    mode: "rectangle"

                NumberInput:
                    id: ind_phone_field
                    hint_text: app.ar("رقم الهاتف")
                    mode: "rectangle"
                    input_filter: "int"
                    halign: "left"

                ArabicInput:
                    id: ind_addr_field
                    hint_text: app.ar("عنوان السكن")
                    mode: "rectangle"


# ------------------------------------------------- تصفّح: المحافظات
<BrowseGovScreen>:
    name: "browse_gov"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            title: app.ar("المحافظات")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("home")]]
        ScrollView:
            MDBoxLayout:
                id: browse_gov_list
                orientation: "vertical"
                padding: dp(12)
                spacing: dp(10)
                adaptive_height: True


# ------------------------------------------------- تصفّح: المؤسسات
<BrowseInstScreen>:
    name: "browse_inst"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: browse_inst_bar
            title: app.ar("المؤسسات")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("browse_gov")]]
        ScrollView:
            MDBoxLayout:
                id: browse_inst_list
                orientation: "vertical"
                padding: dp(12)
                spacing: dp(10)
                adaptive_height: True


# ------------------------------------------------- تصفّح: المعرّفون
<BrowseIndivScreen>:
    name: "browse_indiv"
    MDBoxLayout:
        orientation: "vertical"
        MDTopAppBar:
            id: browse_indiv_bar
            title: app.ar("المعرّفون")
            font_name: app.arabic_font
            elevation: 2
            left_action_items: [["arrow-right", lambda x: app.go("browse_inst")]]
        ScrollView:
            MDBoxLayout:
                id: browse_indiv_list
                orientation: "vertical"
                padding: dp(12)
                spacing: dp(10)
                adaptive_height: True


ScreenManager:
    HomeScreen:
    InstitutionsScreen:
    IndividualsScreen:
    SearchScreen:
    AddInstitutionScreen:
    AddIndividualScreen:
    BrowseGovScreen:
    BrowseInstScreen:
    BrowseIndivScreen:
'''


# ======================================================================
#  التطبيق
# ======================================================================
class MarifinApp(MDApp):

    # متاحة لـ KV عبر app.ar(...) و app.arabic_font — أمتن من الاعتماد على __main__
    arabic_font = ARABIC_FONT

    @staticmethod
    def ar(text):
        return ar(text)

    def build(self):
        self.title = "معرفو المؤسسات الحكومية"
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.material_style = "M3"

        # تطبيق الخط العربي على جميع أنماط KivyMD حتى تستخدمه كل العناصر
        # تلقائياً (الشريط العلوي، القوائم، النوافذ، الأزرار) — عدا أيقونات
        # المواد التي يجب أن تبقى بخطها الخاص.
        if ARABIC_FONT != "Roboto":
            for _style, _val in self.theme_cls.font_styles.items():
                if _style == "Icon":
                    continue
                try:
                    _val[0] = ARABIC_FONT
                except Exception:
                    pass

        db_dir = self.user_data_dir if platform == "android" else "."
        self.db = Database(os.path.join(db_dir, "marifin.db"))

        self._gov_menu = None
        self._ind_gov_menu = None
        self._ind_inst_menu = None

        # حالة التحرير
        self.editing_inst_id = None
        self.editing_ind_id = None
        # الاختيارات الحالية (id الحقيقي)
        self.sel_gov_id = None          # لشاشة إضافة مؤسسة
        self.ind_sel_gov_id = None      # لشاشة إضافة فرد
        self.ind_sel_inst_id = None

        # حالة التصفّح الهرمي (المحافظات ← المؤسسات ← المعرّفون)
        self.browse_gov_id = None
        self.browse_gov_name = ""
        self.browse_inst_id = None
        self.browse_inst_name = ""

        return Builder.load_string(KV)

    # --------------------------------------------------------- التنقل
    def go(self, screen):
        self.root.current = screen
        if screen == "institutions":
            self.refresh_institutions()
        elif screen == "individuals":
            self.refresh_individuals()
        elif screen == "browse_gov":
            self.refresh_browse_gov()
        elif screen == "browse_inst":
            self.refresh_browse_inst()
        elif screen == "browse_indiv":
            self.refresh_browse_indiv()

    def toast(self, msg):
        if Snackbar:
            try:
                Snackbar(text=ar(msg)).open()
                return
            except Exception:
                pass
        print(msg)

    # ------------------------------------------------ قوائم المحافظات
    def _gov_items(self, callback):
        items = []
        for g in self.db.get_governorates():
            items.append({
                "viewclass": "OneLineListItem",
                "text": ar(g["name"]),
                "font_name": ARABIC_FONT,
                "on_release": lambda gid=g["id"], gn=g["name"]: callback(gid, gn),
            })
        return items

    # ===================================================================
    #  المؤسسات
    # ===================================================================
    def refresh_institutions(self):
        box = self.root.get_screen("institutions").ids.inst_list
        box.clear_widgets()
        rows = self.db.get_institutions()
        if not rows:
            box.add_widget(self._empty_label("لا توجد مؤسسات بعد. اضغط + للإضافة."))
            return
        for r in rows:
            sub = "المحافظة: %s   |   القضاء: %s" % (
                r["gov_name"], r["district"] or "—")
            box.add_widget(RecordCard(
                title=r["name"], subtitle=sub, rec_id=r["id"],
                tap_action=self.institution_actions))

    def open_add_institution(self):
        self.editing_inst_id = None
        self.sel_gov_id = None
        scr = self.root.get_screen("add_institution")
        scr.ids.gov_field.set_value("")
        scr.ids.district_field.clear()
        scr.ids.inst_name_field.clear()
        self.root.current = "add_institution"

    def open_gov_menu(self, field):
        if self._gov_menu:
            self._gov_menu.dismiss()
        self._gov_menu = MDDropdownMenu(
            caller=field, width_mult=4,
            items=self._gov_items(self._pick_gov_institution))
        self._gov_menu.open()

    def _pick_gov_institution(self, gov_id, gov_name):
        self.sel_gov_id = gov_id
        scr = self.root.get_screen("add_institution")
        scr.ids.gov_field.set_value(gov_name)
        if self._gov_menu:
            self._gov_menu.dismiss()

    def save_institution(self):
        scr = self.root.get_screen("add_institution")
        name = scr.ids.inst_name_field.get_raw()
        district = scr.ids.district_field.get_raw()
        if not self.sel_gov_id:
            self.toast("اختر المحافظة")
            return
        if not name.strip():
            self.toast("اكتب اسم المؤسسة")
            return
        if self.editing_inst_id:
            self.db.update_institution(
                self.editing_inst_id, name, district, self.sel_gov_id)
            self.toast("تم تعديل المؤسسة")
        else:
            self.db.add_institution(name, district, self.sel_gov_id)
            self.toast("تمت إضافة المؤسسة")
        self.go("institutions")

    def institution_actions(self, inst_id):
        rows = [r for r in self.db.get_institutions() if r["id"] == inst_id]
        if not rows:
            return
        r = rows[0]
        self._record_dialog(
            title=r["name"],
            on_edit=lambda: self._edit_institution(r),
            on_delete=lambda: self._delete_institution(inst_id))

    def _edit_institution(self, r):
        self.editing_inst_id = r["id"]
        self.sel_gov_id = r["governorate_id"]
        scr = self.root.get_screen("add_institution")
        scr.ids.gov_field.set_value(r["gov_name"])
        scr.ids.district_field.set_value(r["district"] or "")
        scr.ids.inst_name_field.set_value(r["name"])
        self.root.current = "add_institution"

    def _delete_institution(self, inst_id):
        self.db.delete_institution(inst_id)
        self.toast("تم الحذف")
        self.refresh_institutions()

    # ===================================================================
    #  الأفراد
    # ===================================================================
    def refresh_individuals(self):
        box = self.root.get_screen("individuals").ids.indiv_list
        box.clear_widgets()
        rows = self.db.get_individuals()
        if not rows:
            box.add_widget(self._empty_label("لا يوجد أفراد بعد. اضغط + للإضافة."))
            return
        for r in rows:
            box.add_widget(self._individual_card(r))

    def _individual_card(self, r):
        sub = "%s  |  %s  |  المؤسسة: %s (%s)" % (
            r["phone"] or "—", r["address"] or "—", r["inst_name"], r["gov_name"])
        return RecordCard(
            title=r["name"], subtitle=sub, rec_id=r["id"],
            tap_action=self.individual_actions)

    def open_add_individual(self):
        if not self.db.get_institutions():
            self.toast("أضف مؤسسة أولاً")
            return
        self.editing_ind_id = None
        self.ind_sel_gov_id = None
        self.ind_sel_inst_id = None
        scr = self.root.get_screen("add_individual")
        for fid in ("ind_gov_field", "ind_inst_field", "ind_name_field",
                    "ind_addr_field"):
            scr.ids[fid].set_value("")
        scr.ids.ind_phone_field.text = ""
        self.root.current = "add_individual"

    def open_ind_gov_menu(self, field):
        if self._ind_gov_menu:
            self._ind_gov_menu.dismiss()
        # أظهر فقط المحافظات التي تحتوي مؤسسات
        gov_ids = {r["governorate_id"] for r in self.db.get_institutions()}
        items = []
        for g in self.db.get_governorates():
            if g["id"] in gov_ids:
                items.append({
                    "viewclass": "OneLineListItem",
                    "text": ar(g["name"]),
                    "font_name": ARABIC_FONT,
                    "on_release": (lambda gid=g["id"], gn=g["name"]:
                                   self._pick_ind_gov(gid, gn)),
                })
        if not items:
            self.toast("لا توجد مؤسسات لأي محافظة")
            return
        self._ind_gov_menu = MDDropdownMenu(
            caller=field, width_mult=4, items=items)
        self._ind_gov_menu.open()

    def _pick_ind_gov(self, gov_id, gov_name):
        self.ind_sel_gov_id = gov_id
        self.ind_sel_inst_id = None
        scr = self.root.get_screen("add_individual")
        scr.ids.ind_gov_field.set_value(gov_name)
        scr.ids.ind_inst_field.set_value("")  # إعادة ضبط المؤسسة
        if self._ind_gov_menu:
            self._ind_gov_menu.dismiss()

    def open_ind_inst_menu(self, field):
        if not self.ind_sel_gov_id:
            self.toast("اختر المحافظة أولاً")
            return
        if self._ind_inst_menu:
            self._ind_inst_menu.dismiss()
        items = []
        for inst in self.db.get_institutions(self.ind_sel_gov_id):
            label = inst["name"]
            if inst["district"]:
                label += " - " + inst["district"]
            items.append({
                "viewclass": "OneLineListItem",
                "text": ar(label),
                "font_name": ARABIC_FONT,
                "on_release": (lambda iid=inst["id"], lb=label:
                               self._pick_ind_inst(iid, lb)),
            })
        self._ind_inst_menu = MDDropdownMenu(
            caller=field, width_mult=4, items=items)
        self._ind_inst_menu.open()

    def _pick_ind_inst(self, inst_id, label):
        self.ind_sel_inst_id = inst_id
        scr = self.root.get_screen("add_individual")
        scr.ids.ind_inst_field.set_value(label)
        if self._ind_inst_menu:
            self._ind_inst_menu.dismiss()

    def save_individual(self):
        scr = self.root.get_screen("add_individual")
        name = scr.ids.ind_name_field.get_raw()
        phone = scr.ids.ind_phone_field.text
        addr = scr.ids.ind_addr_field.get_raw()
        if not self.ind_sel_inst_id:
            self.toast("اختر المحافظة ثم المؤسسة")
            return
        if not name.strip():
            self.toast("اكتب اسم الفرد")
            return
        if self.editing_ind_id:
            self.db.update_individual(
                self.editing_ind_id, name, phone, addr, self.ind_sel_inst_id)
            self.toast("تم تعديل الفرد")
        else:
            self.db.add_individual(name, phone, addr, self.ind_sel_inst_id)
            self.toast("تمت إضافة الفرد")
        self.go("individuals")

    def individual_actions(self, ind_id):
        rows = [r for r in self.db.get_individuals() if r["id"] == ind_id]
        if not rows:
            return
        r = rows[0]
        self._record_dialog(
            title=r["name"],
            on_edit=lambda: self._edit_individual(r),
            on_delete=lambda: self._delete_individual(ind_id))

    def _edit_individual(self, r):
        self.editing_ind_id = r["id"]
        self.ind_sel_gov_id = None  # نحتاج id المحافظة
        for g in self.db.get_governorates():
            if g["name"] == r["gov_name"]:
                self.ind_sel_gov_id = g["id"]
                break
        self.ind_sel_inst_id = r["institution_id"]
        scr = self.root.get_screen("add_individual")
        scr.ids.ind_gov_field.set_value(r["gov_name"])
        inst_label = r["inst_name"] + (
            " - " + r["district"] if r["district"] else "")
        scr.ids.ind_inst_field.set_value(inst_label)
        scr.ids.ind_name_field.set_value(r["name"])
        scr.ids.ind_phone_field.text = r["phone"] or ""
        scr.ids.ind_addr_field.set_value(r["address"] or "")
        self.root.current = "add_individual"

    def _delete_individual(self, ind_id):
        self.db.delete_individual(ind_id)
        self.toast("تم الحذف")
        self.refresh_individuals()

    # ===================================================================
    #  البحث
    # ===================================================================
    def do_search(self, term):
        box = self.root.get_screen("search").ids.search_results
        box.clear_widgets()
        term = (term or "").strip()
        if not term:
            return
        res = self.db.search(term)
        if not res["individuals"] and not res["institutions"]:
            box.add_widget(self._empty_label("لا نتائج"))
            return
        if res["institutions"]:
            box.add_widget(self._section_label("المؤسسات"))
            for r in res["institutions"]:
                sub = "المحافظة: %s  |  القضاء: %s" % (
                    r["gov_name"], r["district"] or "—")
                box.add_widget(RecordCard(
                    title=r["name"], subtitle=sub, rec_id=r["id"],
                    tap_action=self.institution_actions))
        if res["individuals"]:
            box.add_widget(self._section_label("الأفراد"))
            for r in res["individuals"]:
                box.add_widget(self._individual_card(r))

    # ===================================================================
    #  التصفّح الهرمي: المحافظات ← المؤسسات ← المعرّفون
    # ===================================================================
    def refresh_browse_gov(self):
        box = self.root.get_screen("browse_gov").ids.browse_gov_list
        box.clear_widgets()
        # عدّ المؤسسات لكل محافظة لعرضه كعنوان فرعي
        counts = {}
        for inst in self.db.get_institutions():
            counts[inst["governorate_id"]] = counts.get(inst["governorate_id"], 0) + 1
        for g in self.db.get_governorates():
            n = counts.get(g["id"], 0)
            box.add_widget(RecordCard(
                title=g["name"],
                subtitle="%d مؤسسة" % n,
                rec_id=g["id"],
                tap_action=self.open_browse_inst))

    def open_browse_inst(self, gov_id):
        self.browse_gov_id = gov_id
        for g in self.db.get_governorates():
            if g["id"] == gov_id:
                self.browse_gov_name = g["name"]
                break
        self.go("browse_inst")

    def refresh_browse_inst(self):
        scr = self.root.get_screen("browse_inst")
        scr.ids.browse_inst_bar.title = ar(self.browse_gov_name or "المؤسسات")
        box = scr.ids.browse_inst_list
        box.clear_widgets()
        rows = self.db.get_institutions(self.browse_gov_id)
        if not rows:
            box.add_widget(self._empty_label("لا توجد مؤسسات في هذه المحافظة"))
            return
        for r in rows:
            cnt = len(self.db.get_individuals(r["id"]))
            sub = "القضاء: %s   |   %d معرّف" % (r["district"] or "—", cnt)
            box.add_widget(RecordCard(
                title=r["name"], subtitle=sub, rec_id=r["id"],
                tap_action=self.open_browse_indiv))

    def open_browse_indiv(self, inst_id):
        self.browse_inst_id = inst_id
        for r in self.db.get_institutions(self.browse_gov_id):
            if r["id"] == inst_id:
                self.browse_inst_name = r["name"]
                break
        self.go("browse_indiv")

    def refresh_browse_indiv(self):
        scr = self.root.get_screen("browse_indiv")
        scr.ids.browse_indiv_bar.title = ar(self.browse_inst_name or "المعرّفون")
        box = scr.ids.browse_indiv_list
        box.clear_widgets()
        rows = self.db.get_individuals(self.browse_inst_id)
        if not rows:
            box.add_widget(self._empty_label("لا يوجد معرّفون في هذه المؤسسة"))
            return
        for r in rows:
            sub = "الهاتف: %s   |   العنوان: %s" % (
                r["phone"] or "—", r["address"] or "—")
            box.add_widget(RecordCard(
                title=r["name"], subtitle=sub, rec_id=r["id"],
                tap_action=self.individual_actions))

    # ===================================================================
    #  عناصر مساعدة للواجهة
    # ===================================================================
    def _empty_label(self, text):
        return MDLabel(
            text=ar(text), font_name=ARABIC_FONT, halign="center",
            theme_text_color="Hint", adaptive_height=True,
            padding=(0, dp(30)))

    def _section_label(self, text):
        return MDLabel(
            text=ar(text), font_name=ARABIC_FONT, halign="right",
            bold=True, font_style="H6", adaptive_height=True)

    def _record_dialog(self, title, on_edit, on_delete):
        dialog = MDDialog(
            title=ar(title),
            text=ar("اختر إجراءً:"),
            buttons=[
                MDFlatButton(text=ar("تعديل"), font_name=ARABIC_FONT,
                             on_release=lambda *a: (dialog.dismiss(), on_edit())),
                MDFlatButton(text=ar("حذف"), font_name=ARABIC_FONT,
                             theme_text_color="Custom",
                             text_color=(0.8, 0.1, 0.1, 1),
                             on_release=lambda *a: (dialog.dismiss(), on_delete())),
                MDFlatButton(text=ar("إلغاء"), font_name=ARABIC_FONT,
                             on_release=lambda *a: dialog.dismiss()),
            ],
        )
        dialog.open()


if __name__ == "__main__":
    MarifinApp().run()
