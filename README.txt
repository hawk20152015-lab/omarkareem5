الخط Amiri مضمّن هنا ومستخدم افتراضياً (Amiri-Regular.ttf + Amiri-Bold.ttf).

لماذا Amiri تحديداً؟
لأن Kivy لا يطبّق تشكيل OpenType، فنستخدم مكتبة arabic_reshaper التي تحوّل
الحروف إلى «أشكال العرض المتصلة» (Presentation Forms). الخطوط الحديثة مثل
Tajawal و Cairo تعتمد على OpenType وتنقصها بعض هذه الأشكال، فتظهر مربعات □.
أما Amiri و Noto Naskh Arabic و Scheherazade فتغطي هذه الأشكال كاملة.

إن أردت خطاً آخر، تأكّد أنه يغطي نطاق U+FE70–U+FEFF و U+FB50–U+FDFF،
وضعه هنا بأحد الأسماء: Amiri / NotoNaskhArabic / Scheherazade / Lateef.
