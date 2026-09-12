import webbrowser
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QFileDialog, QMessageBox,
    QApplication, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from src.api.models import Article
from src.gui.article_detail import ArticleDetailDialog
from src.utils.exporter import ArticleExporter
from src.utils.config import ConfigManager

class ArticleCardWidget(QFrame):
    """Custom Card UI Widget representing a single academic article."""

    detail_requested = pyqtSignal(Article)
    favorite_toggled = pyqtSignal(Article)

    def __init__(self, article: Article, is_favorite: bool = False, parent=None):
        super().__init__(parent)
        self.article = article
        self.is_favorite = is_favorite
        self.setObjectName("ArticleCard")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header Row: Source Badge, Citations, Year
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        src_badge = QLabel(self.article.source)
        if "+" in self.article.source:
            src_badge.setObjectName("BadgeBoth")
        elif "arXiv" in self.article.source:
            src_badge.setObjectName("BadgeArxiv")
        elif "INSPIRE" in self.article.source:
            src_badge.setObjectName("BadgeInspire")
        else:
            src_badge.setObjectName("BadgeAds")
        top_row.addWidget(src_badge)

        if self.article.citations > 0:
            cit_badge = QLabel(f"⭐ {self.article.citations} Citas")
            cit_badge.setObjectName("BadgeCitations")
            top_row.addWidget(cit_badge)

        if self.article.pub_date:
            date_label = QLabel(f"📅 {self.article.pub_date}")
            date_label.setObjectName("CardMeta")
            top_row.addWidget(date_label)

        if self.article.arxiv_id:
            arxiv_lbl = QLabel(f"arXiv:{self.article.arxiv_id}")
            arxiv_lbl.setObjectName("CardMeta")
            top_row.addWidget(arxiv_lbl)
        elif self.article.inspire_id:
            inspire_lbl = QLabel(f"INSPIRE:{self.article.inspire_id}")
            inspire_lbl.setObjectName("CardMeta")
            top_row.addWidget(inspire_lbl)

        top_row.addStretch()
        layout.addLayout(top_row)

        # Title
        title_label = QLabel(self.article.title)
        title_label.setObjectName("CardTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Authors
        authors_text = ", ".join(self.article.authors[:5])
        if len(self.article.authors) > 5:
            authors_text += f" et al. ({len(self.article.authors)} autores)"
        authors_label = QLabel(f"✍️ {authors_text}")
        authors_label.setObjectName("CardAuthors")
        authors_label.setWordWrap(True)
        layout.addWidget(authors_label)

        # Abstract Snippet
        snippet = self.article.abstract[:220] + "..." if len(self.article.abstract) > 220 else self.article.abstract
        abstract_label = QLabel(snippet)
        abstract_label.setWordWrap(True)
        abstract_label.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(abstract_label)

        # Action Buttons Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        btn_detail = QPushButton("🔍 Detalles / Cita")
        btn_detail.setObjectName("CardActionButton")
        btn_detail.clicked.connect(lambda: self.detail_requested.emit(self.article))
        actions_layout.addWidget(btn_detail)

        if self.article.pdf_url:
            btn_pdf = QPushButton("📄 PDF")
            btn_pdf.setObjectName("CardActionButton")
            btn_pdf.clicked.connect(lambda: webbrowser.open(self.article.pdf_url))
            actions_layout.addWidget(btn_pdf)

        if self.article.url:
            btn_web = QPushButton("🌐 Web")
            btn_web.setObjectName("CardActionButton")
            btn_web.clicked.connect(lambda: webbrowser.open(self.article.url))
            actions_layout.addWidget(btn_web)

        if self.article.url or self.article.pdf_url:
            btn_share = QPushButton("🔗 Compartir Enlace")
            btn_share.setObjectName("CardActionButton")
            btn_share.clicked.connect(self._share_link)
            actions_layout.addWidget(btn_share)

        btn_copy = QPushButton("📋 BibTeX")
        btn_copy.setObjectName("CardActionButton")
        btn_copy.clicked.connect(self._copy_bibtex)
        actions_layout.addWidget(btn_copy)

        self.btn_fav = QPushButton("★ Guardado" if self.is_favorite else "⭐ Favorito")
        if self.is_favorite:
            self.btn_fav.setObjectName("FavoriteButton")
        else:
            self.btn_fav.setObjectName("CardActionButton")
        self.btn_fav.clicked.connect(self._on_fav_clicked)
        actions_layout.addWidget(self.btn_fav)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

    def _share_link(self):
        link = self.article.url or self.article.pdf_url or ""
        if link:
            clipboard = QApplication.clipboard()
            clipboard.setText(link)
            btn = self.sender()
            if isinstance(btn, QPushButton):
                orig_text = btn.text()
                btn.setText("✓ ¡Enlace Copiado!")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1500, lambda: btn.setText(orig_text))

    def _copy_bibtex(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.article.generate_bibtex())
        btn = self.sender()
        if isinstance(btn, QPushButton):
            orig_text = btn.text()
            btn.setText("✓ Copiado")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1200, lambda: btn.setText(orig_text))

    def _on_fav_clicked(self):
        self.favorite_toggled.emit(self.article)


class ResultsView(QWidget):
    """View displaying search results, filtering, sorting, and exporting."""

    gdrive_export_requested = pyqtSignal(list, str)
    gdrive_pdf_requested = pyqtSignal(Article)
    zotero_export_requested = pyqtSignal(list)
    zotero_single_requested = pyqtSignal(Article)
    favorites_changed = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.all_articles: List[Article] = []
        self.displayed_articles: List[Article] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Control Bar
        ctrl_bar = QHBoxLayout()

        self.lbl_count = QLabel("No hay búsquedas recientes")
        self.lbl_count.setObjectName("SectionTitle")
        ctrl_bar.addWidget(self.lbl_count)

        ctrl_bar.addStretch()

        # In-results filter text field
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtrar en resultados...")
        self.filter_input.setFixedWidth(200)
        self.filter_input.textChanged.connect(self._apply_in_results_filter)
        ctrl_bar.addWidget(self.filter_input)

        # Export Button
        btn_export = QPushButton("📥 Exportar...")
        btn_export.clicked.connect(self._show_export_menu)
        ctrl_bar.addWidget(btn_export)

        layout.addLayout(ctrl_bar)

        # Scroll area for article cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

    def set_articles(self, articles: List[Article], source_summary: str = ""):
        self.all_articles = articles
        self.filter_input.clear()
        self._render_articles(self.all_articles, source_summary)

    def refresh(self):
        """Re-renders current results view to sync state changes (e.g. favorite updates)."""
        self._render_articles(self.displayed_articles)

    def _render_articles(self, articles: List[Article], source_summary: str = ""):
        self.displayed_articles = articles

        # Clear existing cards
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not articles:
            lbl_empty = QLabel("No se encontraron artículos con los criterios seleccionados.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 40px;")
            self.cards_layout.addWidget(lbl_empty)
            self.lbl_count.setText("0 artículos")
        else:
            txt_sum = f"({source_summary})" if source_summary else ""
            self.lbl_count.setText(f"📋 {len(articles)} artículos encontrados {txt_sum}")

            for article in articles:
                is_fav = self.config_manager.is_favorite(article.id)
                card = ArticleCardWidget(article, is_favorite=is_fav)
                card.detail_requested.connect(self._show_article_detail)
                card.favorite_toggled.connect(self._toggle_favorite)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _apply_in_results_filter(self, text: str):
        query = text.strip().lower()
        if not query:
            self._render_articles(self.all_articles)
            return

        filtered = [
            a for a in self.all_articles
            if query in a.title.lower() or query in a.abstract.lower() or any(query in au.lower() for au in a.authors)
        ]
        self._render_articles(filtered)

    def _show_article_detail(self, article: Article):
        is_fav = self.config_manager.is_favorite(article.id)
        dialog = ArticleDetailDialog(article, is_favorite=is_fav, parent=self)
        res = dialog.exec()
        if res == 100:  # Code returned when user toggles favorite inside modal
            self._toggle_favorite(article)
        elif res == 101:  # Code returned when user clicks upload PDF to Drive
            self.gdrive_pdf_requested.emit(article)
        elif res == 102:  # Code returned when user clicks upload article to Zotero
            self.zotero_single_requested.emit(article)

    def _toggle_favorite(self, article: Article):
        now_fav = self.config_manager.toggle_favorite(article)
        # Re-render current list to update favorite button icons
        self._render_articles(self.displayed_articles)
        self.favorites_changed.emit()

    def _show_export_menu(self):
        if not self.displayed_articles:
            QMessageBox.information(self, "Exportación", "No hay artículos en la lista para exportar.")
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(self.styleSheet())
        
        act_bib = menu.addAction("📄 Exportar a BibTeX (.bib)")
        act_csv = menu.addAction("📊 Exportar a CSV (.csv)")
        act_json = menu.addAction("⚙️ Exportar a JSON (.json)")
        menu.addSeparator()
        act_gd_bib = menu.addAction("☁️ Subir BibTeX a Google Drive")
        act_gd_csv = menu.addAction("☁️ Subir CSV a Google Drive")
        act_gd_json = menu.addAction("☁️ Subir JSON a Google Drive")
        menu.addSeparator()
        act_zotero = menu.addAction("📚 Sincronizar / Exportar a Zotero")

        action = menu.exec(self.cursor().pos())
        if action == act_bib:
            self._export_to_file("BibTeX Files (*.bib)", ArticleExporter.to_bibtex)
        elif action == act_csv:
            self._export_to_file("CSV Files (*.csv)", ArticleExporter.to_csv)
        elif action == act_json:
            self._export_to_file("JSON Files (*.json)", ArticleExporter.to_json)
        elif action == act_gd_bib:
            self.gdrive_export_requested.emit(self.displayed_articles, "bibtex")
        elif action == act_gd_csv:
            self.gdrive_export_requested.emit(self.displayed_articles, "csv")
        elif action == act_gd_json:
            self.gdrive_export_requested.emit(self.displayed_articles, "json")
        elif action == act_zotero:
            self.zotero_export_requested.emit(self.displayed_articles)

    def _export_to_file(self, filter_str: str, export_func):
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Archivo", "", filter_str)
        if file_path:
            success = export_func(self.displayed_articles, file_path)
            if success:
                QMessageBox.information(self, "Éxito", f"Se han exportado {len(self.displayed_articles)} artículos correctamente.")
            else:
                QMessageBox.critical(self, "Error", "Ocurrió un error al guardar el archivo.")
