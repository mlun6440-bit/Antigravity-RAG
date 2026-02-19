from pypdf import PdfReader

r = PdfReader('data/iso_docs/ASISO55000-20241.pdf')
with open('_page_text2.txt', 'w', encoding='utf-8') as f:
    for i in range(10, 25):
        text = r.pages[i].extract_text()
        if text:
            f.write(f"=== PAGE {i} ===\n")
            f.write(text[:600])
            f.write("\n\n")
print("Done")
