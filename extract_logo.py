import os, glob

os.makedirs("src/dashboard/assets", exist_ok=True)

# Find the PDF by glob since the accented filename is tricky
matches = glob.glob(r"C:\Users\rithv\Downloads\Trochi*.pdf")
print("Found:", matches)

from pypdf import PdfReader
reader = PdfReader(matches[0])
page = reader.pages[0]
xobjects = page["/Resources"]["/XObject"].get_object()
print("XObjects:", list(xobjects.keys()))

saved = []
for i, (name, obj) in enumerate(xobjects.items()):
    xobj = obj.get_object()
    subtype = xobj.get("/Subtype")
    w = xobj.get("/Width")
    h = xobj.get("/Height")
    print(f"  {name}: subtype={subtype}, size={w}x{h}")
    if subtype == "/Image":
        filt = xobj.get("/Filter")
        ext = "jpg" if filt == "/DCTDecode" else "png"
        fname = f"src/dashboard/assets/extracted_{i}_{w}x{h}.{ext}"
        try:
            data = xobj.get_data()
            with open(fname, "wb") as f:
                f.write(data)
            print(f"    -> saved {fname} ({len(data)} bytes)")
            saved.append((fname, w, h))
        except Exception as e:
            # Try raw data
            raw = xobj._data
            fname2 = f"src/dashboard/assets/raw_{i}_{w}x{h}.bin"
            with open(fname2, "wb") as f:
                f.write(raw)
            print(f"    -> raw saved {fname2} ({len(raw)} bytes), error={e}")

print("\nDone. Saved:", saved)
