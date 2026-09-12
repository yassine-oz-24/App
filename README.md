## المتطلبات

- Python 3.8 أو أحدث
- حزمة `requests`

## التثبيت

1. افتح الطرفية في مجلد المشروع:
   
   python -m pip install -r requirements.txt
   

2. لتشغيل التطبيق:
   
   python chat_app.py

## التشغيل على الهاتف عبر Termux

التطبيق يعمل من شاشة طرفية فقط، لذلك يمكن تشغيله على Android باستخدام Termux:

```bash
pkg update
pkg install python git
git clone https://github.com/yassine-oz-24/App.git
cd pychat
python -m pip install -r requirements.txt
python chat_app.py
```

الأوامر الأساسية: `fox lg` لتسجيل الدخول، `fox rg` لإنشاء حساب، `u` للمستخدمين، `g` للمجموعات، `m username` لفتح محادثة، `home` للشاشة الرئيسية، و`q` للخروج.
   
