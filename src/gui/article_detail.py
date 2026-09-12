import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QTabWidget, QWidget, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from src.api.models import Article

class ArticleDetailDialog(QDialog):
    """Detailed modal view for inspecting full abstract, BibTeX, and article links."""

    def __init__(self, article: Article, is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.article = article
        self.is_favorite = is_favorite
        self.setWindowTitle(f"Detalles: {article.title[:60]}...")
        self.setMinimumSize(700, 560)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Badges Layout
        badges_layout = QHBoxLayout()
        
        # Source badge
        src_label = QLabel(self.article.source)
        if "arXiv" in self.article.source and "ADS" in self.article.source:
            src_label.setObjectName("BadgeBoth")
        elif "arXiv" in self.article.source:
            src_label.setObjectName("BadgeArxiv")
        else:
            src_label.setObjectName("BadgeAds")
        badges_layout.addWidget(src_label)

        # Citations badge
        if self.article.citations > 0:
            cit_label = QLabel(f"⭐ {self.article.citations} Citas")
            cit_label.setObjectName("BadgeCitations")
            badges_layout.addWidget(cit_label)

        # Publication date
        if self.article.pub_date:
            date_lbl = QLabel(f"📅 {self.article.pub_date}")
            date_lbl.setObjectName("CardMeta")
            badges_layout.addWidget(date_lbl)

        badges_layout.addStretch()
        layout.addLayout(badges_layout)

        # Title
        title_label = QLabel(self.article.title)
        title_label.setObjectName("CardTitle")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 17px; color: #f8fafc;")
        layout.addWidget(title_label)

        # Authors
        authors_str = ", ".join(self.article.authors) if self.article.authors else "Autores desconocidos"
        authors_label = QLabel(f"✍️  {authors_str}")
        authors_label.setObjectName("CardAuthors")
        authors_label.setWordWrap(True)
        layout.addWidget(authors_label)

        # Identifiers (arXiv ID, Bibcode, DOI, Journal)
        ident_info = []
        if self.article.journal:
            ident_info.append(f"<b>Revista:</b> {self.article.journal}")
        if self.article.arxiv_id:
            ident_info.append(f"<b>arXiv ID:</b> {self.article.arxiv_id}")
        if self.article.bibcode:
            ident_info.append(f"<b>Bibcode:</b> {self.article.bibcode}")
        if self.article.doi:
            ident_info.append(f"<b>DOI:</b> {self.article.doi}")

        if ident_info:
            ident_label = QLabel("  •  ".join(ident_info))
            ident_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
            ident_label.setWordWrap(True)
            layout.addWidget(ident_label)

        # Tabs: Abstract & BibTeX
        tabs = QTabWidget()

        # Tab 1: Abstract
        abstract_tab = QWidget()
        abstract_layout = QVBoxLayout(abstract_tab)
        abstract_layout.setContentsMargins(8, 8, 8, 8)

        abstract_text = QTextEdit()
        abstract_text.setReadOnly(True)
        abstract_text.setText(self.article.abstract)
        abstract_text.setStyleSheet("font-size: 13px; line-height: 1.5; background-color: #1e293b;")
        abstract_layout.addWidget(abstract_text)
        tabs.addTab(abstract_tab, "📝 Resumen")

        # Tab 2: BibTeX
        bibtex_tab = QWidget()
        bibtex_layout = QVBoxLayout(bibtex_tab)
        bibtex_layout.setContentsMargins(8, 8, 8, 8)

        self.bibtex_text = QTextEdit()
        self.bibtex_text.setReadOnly(True)
        self.bibtex_text.setText(self.article.generate_bibtex())
        self.bibtex_text.setStyleSheet("font-family: monospace; font-size: 12px; background-color: #1e293b; color: #a5f3fc;")
        bibtex_layout.addWidget(self.bibtex_text)

        btn_copy_bib = QPushButton("📋 Copiar BibTeX al Portapapeles")
        btn_copy_bib.clicked.connect(self._copy_bibtex)
        bibtex_layout.addWidget(btn_copy_bib)

        tabs.addTab(bibtex_tab, "📖 Cita BibTeX")
        layout.addWidget(tabs)

        # Footer Action Buttons
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)

        if self.article.url:
            btn_web = QPushButton("🌐 Abrir Página Web")
            btn_web.clicked.connect(lambda: webbrowser.open(self.article.url))
            footer_layout.addWidget(btn_web)

        if self.article.pdf_url:
            btn_pdf = QPushButton("📄 Abrir PDF")
            btn_pdf.setObjectName("PrimaryButton")
            btn_pdf.clicked.connect(lambda: webbrowser.open(self.article.pdf_url))
            footer_layout.addWidget(btn_pdf)

            btn_gdrive_pdf = QPushButton("☁️ PDF a Drive")
            btn_gdrive_pdf.setToolTip("Descargar PDF y subir directamente a Google Drive")
            btn_gdrive_pdf.clicked.connect(self._upload_pdf_gdrive)
            footer_layout.addWidget(btn_gdrive_pdf)

        if self.article.url or self.article.pdf_url:
            btn_share = QPushButton("🔗 Compartir Enlace")
            btn_share.clicked.connect(self._share_link)
            footer_layout.addWidget(btn_share)

        btn_zotero = QPushButton("📚 Guardar en Zotero")
        btn_zotero.setToolTip("Enviar metadatos del artículo directamente a su biblioteca de Zotero")
        btn_zotero.clicked.connect(self._upload_zotero)
        footer_layout.addWidget(btn_zotero)

        self.btn_fav = QPushButton("⭐ Favorito" if not self.is_favorite else "★ Quitar Favorito")
        if self.is_favorite:
            self.btn_fav.setObjectName("FavoriteButton")
        self.btn_fav.clicked.connect(self._toggle_favorite)
        footer_layout.addWidget(self.btn_fav)

        footer_layout.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        layout.addLayout(footer_layout)

    def _copy_bibtex(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.bibtex_text.toPlainText())
        btn = self.sender()
        if isinstance(btn, QPushButton):
            orig_text = btn.text()
            btn.setText("✓ ¡Copiado!")
            btn.setEnabled(False)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: (btn.setText(orig_text), btn.setEnabled(True)))

    def _share_link(self):
        link = self.article.url or self.article.pdf_url or ""
        if link:
            clipboard = QApplication.clipboard()
            clipboard.setText(link)
            btn = self.sender()
            if isinstance(btn, QPushButton):
                orig_text = btn.text()
                btn.setText("✓ ¡Enlace Copiado!")
                btn.setEnabled(False)
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1500, lambda: (btn.setText(orig_text), btn.setEnabled(True)))

    def _toggle_favorite(self):
        self.done(100)  # Signal parent to toggle favorite

    def _upload_pdf_gdrive(self):
        self.done(101)  # Signal parent to upload PDF to Google Drive

    def _upload_zotero(self):
        self.done(102)  # Signal parent to upload article to Zotero
