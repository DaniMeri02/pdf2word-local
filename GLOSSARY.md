# pdf2word-locale

Strumento personale che trasforma PDF in documenti Word modificabili, senza che il file lasci mai il dispositivo dell'utente.

## Linguaggio

**PDF digitale**:
PDF il cui testo è codificato come caratteri selezionabili, prodotto da software e non da scanner o fotocamera.
_Evitare_: PDF nativo, PDF testuale

**PDF scansionato**:
PDF composto da immagini di pagine, il cui testo è leggibile solo tramite OCR. Fuori dal perimetro della prima versione.
_Evitare_: PDF immagine

**Conversione**:
Il passaggio da un PDF digitale a un documento DOCX, svolto interamente sul dispositivo dell'utente.
_Evitare_: export, trasformazione, upload

**Motore di conversione**:
Il componente che analizza il PDF e ricostruisce paragrafi, tabelle e immagini nel DOCX.
_Evitare_: convertitore, parser

**Flusso editabile**:
Forma del DOCX in cui il contenuto è fatto di paragrafi e tabelle veri che scorrono e si riadattano quando si modifica il testo.
_Evitare_: layout fluido, reflow

**Layout posizionato**:
Forma del DOCX in cui il contenuto è in caselle collocate a coordinate fisse: aspetto fedele, modifica fragile. Non è l'obiettivo.
_Evitare_: impaginazione identica, copia esatta

**Locale**:
Proprietà per cui il PDF e il DOCX non attraversano mai la rete: restano in memoria o sul disco del dispositivo.
_Evitare_: privato, sicuro, offline (offline indica solo l'assenza di rete, non la garanzia sul file)
