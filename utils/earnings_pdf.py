from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io

class EarningsPdf():
    def __init__(self, save: bool = False, file_path: str = None):
        self.save = save
        if save:
            self.doc = SimpleDocTemplate(file_path,
                                        pagesize=A4,
                                        topMargin=20)
        else:
            self.buffer = io.BytesIO()
            self.doc = SimpleDocTemplate(self.buffer,
                                        pagesize=A4,
                                        topMargin=20)
        self.styles = getSampleStyleSheet()
        self.title_style = self.styles['Title']
        self.normal_style =self.styles['Normal']
        self.elements = []

    def add_paragraph(self, title: str):
        self.elements.append(Paragraph(title, self.styles['Title']))
        self.elements.append(Spacer(1, 20))

    def add_table(self, data: list[list[str]]):
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        self.elements.append(table)
        self.elements.append(Spacer(1, 20)) 

    def build(self):
        self.doc.build(self.elements)
        if not self.save:
            result = self.buffer.getvalue()
            self.buffer.close()
            return result
        return None


# USAGE:

# pdf = EarningsPdf(save=False, file_path="testing_reportlab.pdf")
# pdf.add_paragraph("Titolo 1")
# pdf.add_table([['ID',
#             'Prezzo prod.',
#             'Prezzo base',
#             'IVA prod.',
#             'Costo sped.',
#             'Costo base',
#             'IVA sped.',
#             'Valuta',
#             'Data'
#          ]])
# pdf.add_paragraph("Titolo 2")
# pdf.add_table([['ID',
#             'Prezzo prod.',
#             'Prezzo base',
#             'IVA prod.',
#             'Costo sped.',
#             'Costo base',
#             'IVA sped.',
#             'Valuta',
#             'Data'
#          ]])
# pdf.build()