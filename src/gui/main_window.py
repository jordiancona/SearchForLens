import os
from typing import Optional, List
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QSplitter, QStatusBar, QProgressBar,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt
from src.gui.styles import DARK_STYLESHEET
from src.gui.search_panel import SearchPanel
from src.gui.results_view import ResultsView
from src.gui.favorites_panel import FavoritesPanel
from src.gui.settings_dialog import SettingsDialog
from src.utils.config import ConfigManager
from src.utils.worker import SearchWorker
from src.utils.gdrive_worker import GDriveUploadWorker
from src.utils.zotero_worker import ZoteroUploadWorker
from src.api.models import Article

class MainWindow(QMainWindow):
    """Main application window for SearchForLens."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SearchForLens - Lentes Gravitacionales Fuertes & IA")
        self.resize(1200, 800)

        self.config_manager = ConfigManager()
        self.active_worker: Optional[SearchWorker] = None
        self.gdrive_worker: Optional[GDriveUploadWorker] = None
        self.zotero_worker: Optional[ZoteroUploadWorker] = None

        self.setStyleSheet(DARK_STYLESHEET)
        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # --- TOP HEADER BAR ---
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(8, 4, 8, 4)

        header_title = QLabel("🔭 SearchForLens")
        header_title.setObjectName("AppHeaderTitle")
        top_bar.addWidget(header_title)

        header_sub = QLabel("| Lentes Gravitacionales & Inteligencia Artificial")
        header_sub.setObjectName("AppHeaderSubtitle")
        top_bar.addWidget(header_sub)

        top_bar.addStretch()

        btn_settings = QPushButton("⚙️ Configuración")
        btn_settings.clicked.connect(self._open_settings)
        top_bar.addWidget(btn_settings)

        btn_exit = QPushButton("🚪 Salir")
        btn_exit.setObjectName("ExitButton")
        btn_exit.setToolTip("Cerrar la aplicación")
        btn_exit.clicked.connect(self._confirm_exit)
        top_bar.addWidget(btn_exit)

        main_layout.addLayout(top_bar)

        # --- MAIN TAB NAVIGATION ---
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # --- TAB 1: SEARCH & RESULTS ---
        search_tab = QWidget()
        search_layout = QHBoxLayout(search_tab)
        search_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Search Panel
        self.search_panel = SearchPanel()
        self.search_panel.search_requested.connect(self._on_search_requested)
        splitter.addWidget(self.search_panel)

        # Right Results View
        self.results_view = ResultsView(config_manager=self.config_manager)
        self.results_view.gdrive_export_requested.connect(self._on_gdrive_export_requested)
        self.results_view.gdrive_pdf_requested.connect(self._on_gdrive_pdf_requested)
        self.results_view.zotero_export_requested.connect(self._on_zotero_export_requested)
        self.results_view.zotero_single_requested.connect(self._on_zotero_single_requested)
        self.results_view.favorites_changed.connect(self._on_favorites_changed_in_results)
        splitter.addWidget(self.results_view)

        # Set initial splitter proportion (~32% sidebar, ~68% content)
        splitter.setSizes([360, 840])

        search_layout.addWidget(splitter)
        self.tab_widget.addTab(search_tab, "🔎 Búsqueda de Artículos")

        # --- TAB 2: FAVORITES ---
        self.favorites_panel = FavoritesPanel(config_manager=self.config_manager)
        self.favorites_panel.gdrive_export_requested.connect(self._on_gdrive_export_requested)
        self.favorites_panel.gdrive_pdf_requested.connect(self._on_gdrive_pdf_requested)
        self.favorites_panel.zotero_export_requested.connect(self._on_zotero_export_requested)
        self.favorites_panel.zotero_single_requested.connect(self._on_zotero_single_requested)
        self.favorites_panel.favorites_changed.connect(self._on_favorites_changed_in_panel)
        self.tab_widget.addTab(self.favorites_panel, "⭐ Artículos Favoritos")

        main_layout.addWidget(self.tab_widget)

        # --- STATUS BAR ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_status = QLabel("Sistema listo. Seleccione una consulta y haga clic en Buscar.")
        self.status_bar.addWidget(self.lbl_status, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def _on_tab_changed(self, index: int):
        if index == 1:
            self.favorites_panel.reload_favorites()
        elif index == 0:
            self.results_view.refresh()

    def _on_favorites_changed_in_results(self):
        self.favorites_panel.reload_favorites()

    def _on_favorites_changed_in_panel(self):
        self.results_view.refresh()

    def _open_settings(self):
        dialog = SettingsDialog(self.config_manager, parent=self)
        dialog.exec()

    def _on_search_requested(self, params: dict):
        if self.active_worker and self.active_worker.isRunning():
            QMessageBox.warning(self, "Búsqueda en curso", "Ya hay una búsqueda ejecutándose en este momento.")
            return

        ads_key = self.config_manager.get_ads_api_key()

        # Create QThread worker
        self.active_worker = SearchWorker(
            preset_type=params["preset_type"],
            custom_query=params["custom_query"],
            author=params["author"],
            start_year=params["start_year"],
            end_year=params["end_year"],
            source=params["source"],
            ads_api_key=ads_key,
            max_results=params["max_results"],
            sort_by=params["sort_by"]
        )

        self.active_worker.status_updated.connect(self._update_status)
        self.active_worker.results_ready.connect(self._on_results_ready)
        self.active_worker.error_occurred.connect(self._on_search_error)
        self.active_worker.finished.connect(self._on_worker_finished)

        # UI state during search
        self.search_panel.btn_search.setEnabled(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress animation
        self.progress_bar.setVisible(True)

        self.active_worker.start()

    def _update_status(self, message: str):
        self.lbl_status.setText(message)

    def _on_results_ready(self, articles: list, source_str: str):
        self.results_view.set_articles(articles, source_summary=source_str)
        self.lbl_status.setText(f"✓ Búsqueda completada: {len(articles)} artículos recuperados desde {source_str}.")

    def _on_search_error(self, error_msg: str):
        self.lbl_status.setText(f"❌ Error durante la búsqueda: {error_msg}")
        QMessageBox.critical(self, "Error en la Consulta", error_msg)

    def _on_worker_finished(self):
        self.search_panel.btn_search.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.active_worker = None

    def _confirm_exit(self):
        """Prompt user confirmation and exit the application smoothly."""
        reply = QMessageBox.question(
            self,
            "Salir de la Aplicación",
            "¿Está seguro de que desea salir de SearchForLens?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()

    # --- GOOGLE DRIVE UPLOAD HANDLERS ---
    def _on_gdrive_export_requested(self, articles: list, format_str: str):
        cred_path = self.config_manager.get_gdrive_credentials_path()
        tok_path = self.config_manager.get_gdrive_token_path()
        folder_id = self.config_manager.get_gdrive_folder_id()
        folder_name = self.config_manager.get_gdrive_folder_name()

        if not cred_path and not (tok_path and os.path.exists(tok_path)):
            QMessageBox.warning(
                self,
                "Google Drive No Configurado",
                "Por favor configure su cuenta de Google Drive en ⚙️ Configuración antes de realizar subidas."
            )
            self._open_settings()
            return

        worker = GDriveUploadWorker(
            credentials_path=cred_path,
            token_path=tok_path,
            folder_id=folder_id,
            folder_name=folder_name,
            articles=articles,
            export_format=format_str
        )
        self._start_gdrive_worker(worker)

    def _on_gdrive_pdf_requested(self, article: Article):
        cred_path = self.config_manager.get_gdrive_credentials_path()
        tok_path = self.config_manager.get_gdrive_token_path()
        folder_id = self.config_manager.get_gdrive_folder_id()
        folder_name = self.config_manager.get_gdrive_folder_name()

        if not cred_path and not (tok_path and os.path.exists(tok_path)):
            QMessageBox.warning(
                self,
                "Google Drive No Configurado",
                "Por favor configure su cuenta de Google Drive en ⚙️ Configuración antes de realizar subidas."
            )
            self._open_settings()
            return

        worker = GDriveUploadWorker(
            credentials_path=cred_path,
            token_path=tok_path,
            folder_id=folder_id,
            folder_name=folder_name,
            pdf_article=article
        )
        self._start_gdrive_worker(worker)

    def _start_gdrive_worker(self, worker: GDriveUploadWorker):
        if self.gdrive_worker and self.gdrive_worker.isRunning():
            QMessageBox.warning(self, "Subida en Curso", "Ya hay una subida a Google Drive ejecutándose.")
            return

        self.gdrive_worker = worker
        self.gdrive_worker.status_updated.connect(self._update_status)
        self.gdrive_worker.upload_complete.connect(self._on_gdrive_upload_success)
        self.gdrive_worker.error_occurred.connect(self._on_gdrive_upload_error)
        self.gdrive_worker.finished.connect(lambda: self.progress_bar.setVisible(False))

        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.gdrive_worker.start()

    def _on_gdrive_upload_success(self, uploaded_info: dict):
        name = uploaded_info.get("name", "Archivo")
        link = uploaded_info.get("webViewLink", "")
        self.lbl_status.setText(f"✓ ¡Archivo '{name}' subido con éxito a Google Drive!")

        msg = f"El archivo '{name}' ha sido subido correctamente a tu carpeta de Google Drive."
        if link:
            msg += f"\n\nLink: {link}"
        
        reply = QMessageBox.information(
            self,
            "Subida Exitosa a Google Drive",
            msg,
            QMessageBox.StandardButton.Ok
        )

    def _on_gdrive_upload_error(self, error_msg: str):
        self.lbl_status.setText(f"❌ Error al subir a Google Drive: {error_msg}")
        QMessageBox.critical(self, "Error en Google Drive", error_msg)

    # --- ZOTERO UPLOAD HANDLERS ---
    def _on_zotero_export_requested(self, articles: list):
        uid = self.config_manager.get_zotero_user_id()
        key = self.config_manager.get_zotero_api_key()

        if not uid or not key:
            QMessageBox.warning(
                self,
                "Zotero No Configurado",
                "Por favor configure su User ID y API Key de Zotero en ⚙️ Configuración antes de sincronizar."
            )
            self._open_settings()
            return

        worker = ZoteroUploadWorker(user_id=uid, api_key=key, articles=articles)
        self._start_zotero_worker(worker)

    def _on_zotero_single_requested(self, article: Article):
        uid = self.config_manager.get_zotero_user_id()
        key = self.config_manager.get_zotero_api_key()

        if not uid or not key:
            QMessageBox.warning(
                self,
                "Zotero No Configurado",
                "Por favor configure su User ID y API Key de Zotero en ⚙️ Configuración antes de guardar."
            )
            self._open_settings()
            return

        worker = ZoteroUploadWorker(user_id=uid, api_key=key, article=article)
        self._start_zotero_worker(worker)

    def _start_zotero_worker(self, worker: ZoteroUploadWorker):
        if self.zotero_worker and self.zotero_worker.isRunning():
            QMessageBox.warning(self, "Sincronización en Curso", "Ya hay una sincronización con Zotero ejecutándose.")
            return

        self.zotero_worker = worker
        self.zotero_worker.status_updated.connect(self._update_status)
        self.zotero_worker.upload_complete.connect(self._on_zotero_upload_success)
        self.zotero_worker.error_occurred.connect(self._on_zotero_upload_error)
        self.zotero_worker.finished.connect(lambda: self.progress_bar.setVisible(False))

        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.zotero_worker.start()

    def _on_zotero_upload_success(self, res: dict):
        title = res.get("title")
        count = res.get("count", 1)

        if title:
            msg = f"✓ ¡Artículo '{title[:50]}...' guardado correctamente en tu biblioteca de Zotero!"
        else:
            msg = f"✓ ¡Sincronización completada! {count} artículos añadidos a tu biblioteca de Zotero."

        self.lbl_status.setText(msg)
        QMessageBox.information(self, "Zotero Sincronizado", msg)

    def _on_zotero_upload_error(self, error_msg: str):
        self.lbl_status.setText(f"❌ Error al conectar con Zotero: {error_msg}")
        QMessageBox.critical(self, "Error en Zotero", error_msg)
