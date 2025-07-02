from docx import Document

doc = Document("C:/Users/murim/Desktop/VALUTION/NGEI.docx")
for para in doc.paragraphs:
    print(para.text)
