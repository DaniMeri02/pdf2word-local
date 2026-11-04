# pdf2word-local

Personal tool that turns PDFs into editable Word documents without the file ever leaving the user's device.

## Language

**Digital PDF**:
A PDF whose text is encoded as selectable characters, produced by software rather than by a scanner or camera.
_Avoid_: native PDF, text PDF

**Scanned PDF**:
A PDF made of page images, whose text is readable only through OCR. Out of scope for the first version.
_Avoid_: image PDF

**Conversion**:
Turning a digital PDF into a DOCX document, carried out entirely on the user's device.
_Avoid_: export, transformation, upload

**Conversion engine**:
The component that analyses the PDF and rebuilds paragraphs, tables and images in the DOCX.
_Avoid_: converter, parser

**Editable flow**:
A DOCX form in which content is made of real paragraphs and tables that flow and reflow when text is edited.
_Avoid_: fluid layout, reflow

**Positioned layout**:
A DOCX form in which content sits in boxes at fixed coordinates: faithful look, fragile editing. Not the goal.
_Avoid_: identical layout, exact copy

**Local**:
The property that the PDF and the DOCX never cross the network: they stay in memory or on the device's storage.
_Avoid_: private, secure, offline (offline only means no network, not a guarantee about the file)
