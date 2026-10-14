# Template execution contract

## Reference and inspection

- Reference: `C:\Users\mohit\Desktop\Fingerprint_Interim_Project_Report_I_Final_Tables (1).docx`.
- SHA-256 and size must be rechecked immediately before authoring.
- Read-only inspection: `python-docx` package inspection, section audit, paragraph/table inventory, and media inventory.
- Reference has 1 portrait section, US Letter (8.50 x 11.00 in), margins L/R 0.90 in, top 0.80 in, bottom 0.75 in; header/footer distances/style values to be preserved.
- Header is blank. Footer carries the report title/topic and must be changed to the UPI report title while retaining its source paragraph formatting.
- A page render was attempted with the supplied renderer but cannot complete because LibreOffice (`soffice.exe`) is unavailable. Exact pagination and page count remain unknown; the source DOCX and output must retain the same page geometry and section count.

## Page and content patterns

- Cover: source logo, centered interim-report label/title, degree/program block, year, guide/student line, institution and date. Replace fingerprint project title with UPI title; retain known degree/institution values. Keep unknown guide/admission values visibly bracketed.
- Progress form: keep guide/examiner-only assessment and signatures blank; update project metadata and student-entered progress.
- Synopsis: preserve heading and compact synopsis block; replace title, abstract summary, problem, objectives, methodology, results/limitations, and keywords.
- Front matter: preserve table-of-contents, figures, tables, symbols/abbreviations components and their source table styling; update entries to the new chapter/figure/table structure.
- Main report: preserve numbered chapter hierarchy and source `Heading 1`, `Heading 2`, `Heading 3` styles. Organize chapters in order: Introduction; Literature Review; Proposed Methodology; Software Implementation; Results, Discussion and Future Work; Conclusion; References.
- Tables: preserve the source table typography, borders, shading, and cell alignment while replacing content. Include dataset/profile and objective status, related-work comparison, research gaps, model configuration, performance metrics/confusion matrix, technology stack, and abbreviations.
- Figures: retain the source cover logo relationship; replace or repurpose body figures as UPI methodology workflow, confusion matrix, ROC curve, and model feature importance. Keep figure labels/captions adjacent to images.
- Preserve source page size, margins, styles, numbering, section/header/footer parts, and unused package resources unless a documented content slot requires replacement.

## Factual/content boundaries

- Project evidence: `D:\UPI\archive\dataset.csv`, project code and trained metrics in `D:\UPI\UPI_Fraud_Detection_Research_Paper.docx` and `D:\UPI\app`.
- Use verified experiment values only: 250,000 records; 125,016 fraud and 124,984 legitimate labels; stratified 80/20 split (200,000/50,000); accuracy 0.92982; precision 0.9309488; recall 0.9285286; F1 0.9297371; ROC AUC 0.9300083; matrix [[23275,1722],[1787,23216]].
- Explicitly discuss 50.0064% file-level fraud prevalence, absent dataset provenance/label protocol, possible target leakage through risk_score, and limitations of a random row split. Do not claim generalization to operational UPI fraud rates.
- User supplied two identical copies of the same UPI fraud paper; cite the source chapter once. Add accurate primary references for random forests, ROC analysis, and scikit-learn. Do not reuse unsupported metrics from the sample report.
- Author name may be shown as Mohit Singh (consistent with the supplied account context). Do not invent guide or admission details.

## Fidelity and QA gates

- Final output: `D:\UPI\UPI_Fraud_Detection_Interim_Project_Report.docx`; keep the reference file byte-for-byte unchanged.
- Verify the source checksum before creation.
- Verify document structure, paragraphs, tables, figure relationships, section geometry, and unchanged preserve-only parts after creation.
- Attempt final render using `render_docx.py`. If the renderer remains unavailable, report this limit rather than claiming visual page QA.
