from pathlib import Path
import re
root = Path(r"C:\Users\user\Desktop\Организация\Проекты\КОДИНГ\таисия")
js = next((root/"dist/assets").glob("index-*.js"))
s = js.read_text(encoding="utf-8")
print("file", js.name)
print("K", "const t=\"/eslavia/\"" in s or 'const t="/eslavia/"' in s)
for m in re.finditer(r"basename:\"(/[^\"]*)\"", s):
    print("basename", m.group(1))
# also single-quote
for m in re.finditer(r"basename:'(/[^']*)'", s):
    print("basename'", m.group(1))
idx = s.find("createRoot")
print("around createRoot", repr(s[idx:idx+200]) if idx>=0 else None)
print("phone", "79016940148" in s)
print("ogrnip", "323370000044608" in s)
