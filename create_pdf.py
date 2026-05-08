from fpdf import FPDF, XPos, YPos

pdf = FPDF()
pdf.set_margins(15, 15, 15)
pdf.add_page()

pdf.set_font("Helvetica", "B", 16)
pdf.cell(0, 10, "Guide de la Paie", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
pdf.ln(4)

sections = [
    ("Composition du salaire brut", [
        "Salaire de base : montant fixe defini dans votre contrat.",
        "Primes de performance : versees trimestriellement selon les objectifs.",
        "Heures supplementaires : +25% pour les 8 premieres heures, +50% au-dela.",
        "Indemnites transport : remboursement 50% du titre de transport.",
    ]),
    ("Cotisations sociales", [
        "Assurance maladie : 0.75%",
        "Retraite de base : 6.90%",
        "Retraite complementaire : 3.93%",
        "CSG/CRDS : 9.70%",
    ]),
    ("Net a payer", [
        "Salaire net = Salaire brut moins le total des cotisations salariales.",
    ]),
    ("Dates de versement", [
        "Verse le dernier jour ouvrable du mois.",
        "En cas de jour ferie, virement effectue la veille.",
    ]),
    ("Bulletin dematerialise", [
        "Disponible dans votre espace RH des le 25 du mois.",
        "En cas d erreur, contactez le service paie sous 30 jours.",
    ]),
]

for title, lines in sections:
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        pdf.multi_cell(0, 7, "  - " + line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

pdf.output("docs_test/guide_paie.pdf")
print("PDF cree : docs_test/guide_paie.pdf")
