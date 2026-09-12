import os
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QMessageBox, QFileDialog, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from src.utils.config import ConfigManager
from src.api.ads_client import AdsClient
from src.api.gdrive_client import GDriveClient
from src.api.zotero_client import ZoteroClient

class SettingsDialog(QDialog):
    """Configuration window to manage NASA ADS API Token, Google Drive, and Zotero settings."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.ads_client = AdsClient()
        self.gdrive_client = GDriveClient()
        self.zotero_client = ZoteroClient()
        self.setWindowTitle("Configuración & API Keys")
        self.setMinimumSize(600, 480)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title_lbl = QLabel("⚙️ Configuración del Sistema")
        title_lbl.setObjectName("SectionTitle")
        layout.addWidget(title_lbl)

        # Tabs for NASA ADS vs Google Drive
        tabs = QTabWidget()

        # --- TAB 1: NASA ADS ---
        ads_tab = QWidget()
        ads_layout = QVBoxLayout(ads_tab)
        ads_layout.setContentsMargins(12, 12, 12, 12)
        ads_layout.setSpacing(12)

        info_lbl = QLabel(
            "La API de NASA ADS es gratuita pero requiere un Token de acceso.\n"
            "arXiv NO requiere ninguna clave."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        ads_layout.addWidget(info_lbl)

        key_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Pegue aquí su API Token de NASA ADS")
        self.key_input.setText(self.config_manager.get_ads_api_key())
        key_layout.addWidget(self.key_input)

        self.btn_toggle_vis = QPushButton("👁️")
        self.btn_toggle_vis.setFixedWidth(40)
        self.btn_toggle_vis.setToolTip("Mostrar/Ocultar API Key")
        self.btn_toggle_vis.clicked.connect(self._toggle_key_visibility)
        key_layout.addWidget(self.btn_toggle_vis)
        ads_layout.addLayout(key_layout)

        # Test key button & Status label
        test_layout = QHBoxLayout()
        self.btn_test_ads = QPushButton("🧪 Probar API Key NASA ADS")
        self.btn_test_ads.clicked.connect(self._test_ads_key)
        test_layout.addWidget(self.btn_test_ads)

        self.lbl_ads_status = QLabel("")
        self.lbl_ads_status.setWordWrap(True)
        test_layout.addWidget(self.lbl_ads_status)
        test_layout.addStretch()
        ads_layout.addLayout(test_layout)

        # Link to get free NASA ADS key
        btn_link = QPushButton("🔗 Conseguir una API Key gratuita en NASA ADS")
        btn_link.setStyleSheet("text-align: left; color: #38bdf8; background: transparent; border: none;")
        btn_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_link.clicked.connect(lambda: webbrowser.open("https://ui.adsabs.harvard.edu/user/settings/token"))
        ads_layout.addWidget(btn_link)

        ads_layout.addStretch()
        tabs.addTab(ads_tab, "🚀 NASA ADS API")

        # --- TAB 2: GOOGLE DRIVE ---
        gdrive_tab = QWidget()
        gdrive_layout = QVBoxLayout(gdrive_tab)
        gdrive_layout.setContentsMargins(12, 12, 12, 12)
        gdrive_layout.setSpacing(12)

        gdrive_info = QLabel(
            "Conecte su cuenta de Google Drive para subir listas de citas (.bib, .csv, .json) y PDFs de artículos directamente a su nube."
        )
        gdrive_info.setWordWrap(True)
        gdrive_info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        gdrive_layout.addWidget(gdrive_info)

        # File selector for credentials.json
        cred_label = QLabel("Archivo de Credenciales OAuth (credentials.json):")
        gdrive_layout.addWidget(cred_label)

        cred_file_layout = QHBoxLayout()
        self.input_cred_path = QLineEdit()
        self.input_cred_path.setPlaceholderText("Ruta a credentials.json de Google Cloud Console")
        self.input_cred_path.setText(self.config_manager.get_gdrive_credentials_path())
        cred_file_layout.addWidget(self.input_cred_path)

        btn_browse_cred = QPushButton("📁 Buscar...")
        btn_browse_cred.clicked.connect(self._browse_credentials_file)
        cred_file_layout.addWidget(btn_browse_cred)
        gdrive_layout.addLayout(cred_file_layout)

        # Connect button & Status
        conn_layout = QHBoxLayout()
        self.btn_connect_gdrive = QPushButton("🔗 Conectar Cuenta de Google Drive")
        self.btn_connect_gdrive.clicked.connect(self._connect_gdrive)
        conn_layout.addWidget(self.btn_connect_gdrive)

        self.lbl_gdrive_status = QLabel("")
        self.lbl_gdrive_status.setWordWrap(True)
        conn_layout.addWidget(self.lbl_gdrive_status)
        conn_layout.addStretch()
        gdrive_layout.addLayout(conn_layout)

        # Folder settings
        folder_group = QGroupBox("Carpeta Destino en Google Drive")
        folder_layout = QVBoxLayout()

        folder_name_lbl = QLabel("Nombre, ID o Enlace de la Carpeta en Drive:")
        self.input_folder_name = QLineEdit()
        self.input_folder_name.setPlaceholderText("Ej. NombreDeCarpeta, ID de carpeta o https://drive.google.com/...")
        self.input_folder_name.setText(self.config_manager.get_gdrive_folder_name())
        folder_layout.addWidget(folder_name_lbl)
        folder_layout.addWidget(self.input_folder_name)

        btn_create_folder = QPushButton("📂 Verificar / Vincular Carpeta en Drive")
        btn_create_folder.clicked.connect(self._verify_or_create_gdrive_folder)
        folder_layout.addWidget(btn_create_folder)

        folder_group.setLayout(folder_layout)
        gdrive_layout.addWidget(folder_group)

        gdrive_layout.addStretch()
        tabs.addTab(gdrive_tab, "☁️ Google Drive API")

        # --- TAB 3: ZOTERO API ---
        zotero_tab = QWidget()
        zotero_layout = QVBoxLayout(zotero_tab)
        zotero_layout.setContentsMargins(12, 12, 12, 12)
        zotero_layout.setSpacing(12)

        zotero_info = QLabel(
            "Sincronice sus artículos de investigación con su biblioteca de Zotero usando la Web API v3.\n"
            "Requiere su Zotero User ID y una API Key con permisos de escritura."
        )
        zotero_info.setWordWrap(True)
        zotero_info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        zotero_layout.addWidget(zotero_info)

        # User ID Input
        uid_label = QLabel("Zotero User ID (numérico):")
        zotero_layout.addWidget(uid_label)
        self.input_zotero_user_id = QLineEdit()
        self.input_zotero_user_id.setPlaceholderText("Ej. 1234567")
        self.input_zotero_user_id.setText(self.config_manager.get_zotero_user_id())
        zotero_layout.addWidget(self.input_zotero_user_id)

        # API Key Input
        key_label = QLabel("Zotero API Key (con permiso de escritura):")
        zotero_layout.addWidget(key_label)
        zotero_key_layout = QHBoxLayout()
        self.input_zotero_api_key = QLineEdit()
        self.input_zotero_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_zotero_api_key.setPlaceholderText("Pegue aquí su API Key de Zotero")
        self.input_zotero_api_key.setText(self.config_manager.get_zotero_api_key())
        zotero_key_layout.addWidget(self.input_zotero_api_key)

        self.btn_toggle_zotero_vis = QPushButton("👁️")
        self.btn_toggle_zotero_vis.setFixedWidth(40)
        self.btn_toggle_zotero_vis.clicked.connect(self._toggle_zotero_key_visibility)
        zotero_key_layout.addWidget(self.btn_toggle_zotero_vis)
        zotero_layout.addLayout(zotero_key_layout)

        # Test Zotero Connection button & Status
        zotero_test_layout = QHBoxLayout()
        self.btn_test_zotero = QPushButton("🧪 Probar Conexión con Zotero")
        self.btn_test_zotero.clicked.connect(self._test_zotero_connection)
        zotero_test_layout.addWidget(self.btn_test_zotero)

        self.lbl_zotero_status = QLabel("")
        self.lbl_zotero_status.setWordWrap(True)
        zotero_test_layout.addWidget(self.lbl_zotero_status)
        zotero_test_layout.addStretch()
        zotero_layout.addLayout(zotero_test_layout)

        # Link to create Zotero API key
        btn_zotero_link = QPushButton("🔗 Crear o consultar API Key en Zotero.org")
        btn_zotero_link.setStyleSheet("text-align: left; color: #38bdf8; background: transparent; border: none;")
        btn_zotero_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_zotero_link.clicked.connect(lambda: webbrowser.open("https://www.zotero.org/settings/keys"))
        zotero_layout.addWidget(btn_zotero_link)

        zotero_layout.addStretch()
        tabs.addTab(zotero_tab, "📚 Zotero API")

        layout.addWidget(tabs)

        # Check existing GDrive connection status
        self._check_initial_gdrive_status()

        # Footer Buttons
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(btn_cancel)

        btn_save = QPushButton("💾 Guardar Cambios")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self._save_settings)
        footer_layout.addWidget(btn_save)

        layout.addLayout(footer_layout)

    def _toggle_key_visibility(self):
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_vis.setText("🙈")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_vis.setText("👁️")

    def _test_ads_key(self):
        token = self.key_input.text().strip()
        if not token:
            self.lbl_ads_status.setText("⚠️ Ingrese una API key antes de probar.")
            self.lbl_ads_status.setStyleSheet("color: #fbbf24;")
            return

        self.lbl_ads_status.setText("Conectando con NASA ADS...")
        self.lbl_ads_status.setStyleSheet("color: #38bdf8;")
        self.repaint()

        valid, msg = self.ads_client.verify_api_key(token)
        if valid:
            self.lbl_ads_status.setText(f"✓ {msg}")
            self.lbl_ads_status.setStyleSheet("color: #4ade80; font-weight: bold;")
        else:
            self.lbl_ads_status.setText(f"❌ {msg}")
            self.lbl_ads_status.setStyleSheet("color: #f87171; font-weight: bold;")

    def _browse_credentials_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar credentials.json", "", "JSON Files (*.json)"
        )
        if file_path:
            self.input_cred_path.setText(file_path)

    def _check_initial_gdrive_status(self):
        tok_path = self.config_manager.get_gdrive_token_path()
        connected, msg = self.gdrive_client.check_connection(tok_path)
        if connected:
            self.lbl_gdrive_status.setText(f"✓ {msg}")
            self.lbl_gdrive_status.setStyleSheet("color: #4ade80; font-weight: bold;")
        else:
            self.lbl_gdrive_status.setText("⚠️ Google Drive no conectado.")
            self.lbl_gdrive_status.setStyleSheet("color: #94a3b8;")

    def _connect_gdrive(self):
        cred_path = self.input_cred_path.text().strip()
        tok_path = self.config_manager.get_gdrive_token_path()

        if not cred_path or not os.path.exists(cred_path):
            QMessageBox.warning(
                self,
                "Credenciales Requeridas",
                "Por favor seleccione primero el archivo 'credentials.json' descargado desde Google Cloud Console."
            )
            return

        self.lbl_gdrive_status.setText("Abriendo inicio de sesión de Google en el navegador...")
        self.lbl_gdrive_status.setStyleSheet("color: #38bdf8;")
        self.repaint()

        success, msg = self.gdrive_client.authenticate(credentials_path=cred_path, token_path=tok_path)
        if success:
            self.config_manager.set_gdrive_credentials_path(cred_path)
            self.lbl_gdrive_status.setText(f"✓ {msg}")
            self.lbl_gdrive_status.setStyleSheet("color: #4ade80; font-weight: bold;")
            QMessageBox.information(self, "Éxito", msg)
        else:
            self.lbl_gdrive_status.setText(f"❌ {msg}")
            self.lbl_gdrive_status.setStyleSheet("color: #f87171; font-weight: bold;")
            QMessageBox.critical(self, "Error de Conexión", msg)

    def _verify_or_create_gdrive_folder(self):
        tok_path = self.config_manager.get_gdrive_token_path()
        connected, _ = self.gdrive_client.check_connection(tok_path)
        if not connected:
            QMessageBox.warning(self, "Google Drive", "Conecte primero su cuenta de Google Drive.")
            return

        user_input = self.input_folder_name.text().strip() or "SearchForLens"
        folder_id, res_name = self.gdrive_client.verify_or_find_folder(user_input)

        if folder_id:
            self.config_manager.set_gdrive_folder_id(folder_id)
            self.config_manager.set_gdrive_folder_name(res_name)
            QMessageBox.information(
                self, "Google Drive", f"✓ Carpeta '{res_name}' vinculada correctamente en Google Drive.\nID: {folder_id}"
            )
        else:
            QMessageBox.critical(self, "Error", res_name)

    def _toggle_zotero_key_visibility(self):
        if self.input_zotero_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_zotero_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_zotero_vis.setText("🙈")
        else:
            self.input_zotero_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_zotero_vis.setText("👁️")

    def _test_zotero_connection(self):
        uid = self.input_zotero_user_id.text().strip()
        key = self.input_zotero_api_key.text().strip()

        if not uid or not key:
            self.lbl_zotero_status.setText("⚠️ Ingrese su User ID y API Key de Zotero.")
            self.lbl_zotero_status.setStyleSheet("color: #fbbf24;")
            return

        self.lbl_zotero_status.setText("Conectando con Zotero Web API v3...")
        self.lbl_zotero_status.setStyleSheet("color: #38bdf8;")
        self.repaint()

        valid, msg = self.zotero_client.verify_credentials(uid, key)
        if valid:
            self.lbl_zotero_status.setText(f"✓ {msg}")
            self.lbl_zotero_status.setStyleSheet("color: #4ade80; font-weight: bold;")
        else:
            self.lbl_zotero_status.setText(f"❌ {msg}")
            self.lbl_zotero_status.setStyleSheet("color: #f87171; font-weight: bold;")

    def _save_settings(self):
        token = self.key_input.text().strip()
        self.config_manager.set_ads_api_key(token)

        cred_path = self.input_cred_path.text().strip()
        self.config_manager.set_gdrive_credentials_path(cred_path)

        user_folder = self.input_folder_name.text().strip() or "SearchForLens"
        self.config_manager.set_gdrive_folder_name(user_folder)

        # Zotero Settings
        z_uid = self.input_zotero_user_id.text().strip()
        z_key = self.input_zotero_api_key.text().strip()
        self.config_manager.set_zotero_user_id(z_uid)
        self.config_manager.set_zotero_api_key(z_key)

        # Automatically verify and update folder_id on save if connected
        tok_path = self.config_manager.get_gdrive_token_path()
        connected, _ = self.gdrive_client.check_connection(tok_path)
        if connected:
            folder_id, res_name = self.gdrive_client.verify_or_find_folder(user_folder)
            if folder_id:
                self.config_manager.set_gdrive_folder_id(folder_id)
                self.config_manager.set_gdrive_folder_name(res_name)

        QMessageBox.information(self, "Configuración", "La configuración ha sido guardada correctamente.")
        self.accept()
