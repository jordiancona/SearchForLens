from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QScrollArea, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from src.api.models import Article
from src.gui.results_view import ArticleCardWidget
from src.gui.article_detail import ArticleDetailDialog
from src.utils.exporter import ArticleExporter
from src.utils.config import ConfigManager

class FavoritesPanel(QWidget):
    """Panel for managing, viewing, filtering, and exporting favorited articles."""

    favorites_changed = pyqtSignal()
    gdrive_export_requested = pyqtSignal(list, str)
    gdrive_pdf_requested = pyqtSignal(Article)
    zotero_export_requested = pyqtSignal(list)
    zotero_single_requested = pyqtSignal(Article)

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.favorites: List[Article] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Control Bar
        ctrl_bar = QHBoxLayout()

        self.lbl_title = QLabel("⭐ Artículos Guardados (Favoritos)")
        self.lbl_title.setObjectName("SectionTitle")
        ctrl_bar.addWidget(self.lbl_title)

        ctrl_bar.addStretch()

        # Search inside favorites
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Buscar en favoritos...")
        self.filter_input.setFixedWidth(200)
        self.filter_input.textChanged.connect(self._apply_filter)
        ctrl_bar.addWidget(self.filter_input)

        btn_export = QPushButton("📥 Exportar Favoritos...")
        btn_export.clicked.connect(self._show_export_menu)
        ctrl_bar.addWidget(btn_export)

        layout.addLayout(ctrl_bar)

        # Scroll area
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

        self.reload_favorites()

    def reload_favorites(self):
        self.favorites = self.config_manager.get_favorites()
        self._apply_filter(self.filter_input.text())

    def _apply_filter(self, text: str = ""):
        query = text.strip().lower()
        if not query:
            self._render_cards(self.favorites)
            return

        filtered = [
            a for a in self.favorites
            if query in a.title.lower() or query in a.abstract.lower() or any(query in au.lower() for au in a.authors)
        ]
        self._render_cards(filtered)

    def _render_cards(self, articles: List[Article]):
        # Clear existing layout items
        while self.cards_layout.count():
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not articles:
            lbl_empty = QLabel("No hay artículos guardados en Favoritos.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 40px;")
            self.cards_layout.addWidget(lbl_empty)
            self.lbl_title.setText("⭐ Artículos Guardados (0)")
        else:
            self.lbl_title.setText(f"⭐ Artículos Guardados ({len(articles)})")
            for article in articles:
                card = ArticleCardWidget(article, is_favorite=True)
                card.detail_requested.connect(self._show_article_detail)
                card.favorite_toggled.connect(self._remove_favorite)
                self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()

    def _show_article_detail(self, article: Article):
        dialog = ArticleDetailDialog(article, is_favorite=True, parent=self)
        res = dialog.exec()
        if res == 100:  # code when favorite is toggled inside detail view
            self._remove_favorite(article)
        elif res == 101:  # code when user requests PDF upload to Google Drive
            self.gdrive_pdf_requested.emit(article)
        elif res == 102:  # code when user requests upload to Zotero
            self.zotero_single_requested.emit(article)

    def _remove_favorite(self, article: Article):
        self.config_manager.remove_favorite(article.id)
        self.reload_favorites()
        self.favorites_changed.emit()

    def _show_export_menu(self):
        if not self.favorites:
            QMessageBox.information(self, "Exportación", "No hay artículos en Favoritos para exportar.")
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(self.styleSheet())

        act_bib = menu.addAction("📄 Exportar Favoritos a BibTeX (.bib)")
        act_csv = menu.addAction("📊 Exportar Favoritos a CSV (.csv)")
        act_json = menu.addAction("⚙️ Exportar Favoritos a JSON (.json)")
        menu.addSeparator()
        act_gd_bib = menu.addAction("☁️ Subir Favoritos BibTeX a Google Drive")
        act_gd_csv = menu.addAction("☁️ Subir Favoritos CSV a Google Drive")
        act_gd_json = menu.addAction("☁️ Subir Favoritos JSON a Google Drive")
        menu.addSeparator()
        act_zotero = menu.addAction("📚 Sincronizar Favoritos a Zotero")

        action = menu.exec(self.cursor().pos())
        if action == act_bib:
            self._export_to_file("BibTeX Files (*.bib)", ArticleExporter.to_bibtex)
        elif action == act_csv:
            self._export_to_file("CSV Files (*.csv)", ArticleExporter.to_csv)
        elif action == act_json:
            self._export_to_file("JSON Files (*.json)", ArticleExporter.to_json)
        elif action == act_gd_bib:
            self.gdrive_export_requested.emit(self.favorites, "bibtex")
        elif action == act_gd_csv:
            self.gdrive_export_requested.emit(self.favorites, "csv")
        elif action == act_gd_json:
            self.gdrive_export_requested.emit(self.favorites, "json")
        elif action == act_zotero:
            self.zotero_export_requested.emit(self.favorites)

    def _export_to_file(self, filter_str: str, export_func):
        file_path, _ = QFileDialog.getSaveFileName(self, "Guardar Favoritos", "", filter_str)
        if file_path:
            success = export_func(self.favorites, file_path)
            if success:
                QMessageBox.information(self, "Éxito", f"Se han exportado {len(self.favorites)} artículos a {file_path}.")
            else:
                QMessageBox.critical(self, "Error", "Ocurrió un error al guardar los favoritos.")
