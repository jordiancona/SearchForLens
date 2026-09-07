import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/search_provider.dart';
import '../services/ads_service.dart';

class SettingsView extends StatefulWidget {
  const SettingsView({super.key});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  late TextEditingController _adsKeyCtrl;
  bool _isTestingToken = false;
  String? _adsStatusMsg;

  @override
  void initState() {
    super.initState();
    final provider = Provider.of<SearchProvider>(context, listen: false);
    _adsKeyCtrl = TextEditingController(text: provider.adsApiKey);
  }

  Future<void> _verifyAdsKey() async {
    setState(() {
      _isTestingToken = true;
      _adsStatusMsg = null;
    });

    final adsService = AdsService();
    final valid = await adsService.verifyApiKey(_adsKeyCtrl.text);

    setState(() {
      _isTestingToken = false;
      _adsStatusMsg = valid
          ? '✅ API Key de NASA ADS válida. Conexión exitosa.'
          : '❌ API Key inválida o sin permisos.';
    });
  }

  Future<void> _openNasaAdsTokenPage() async {
    final Uri url = Uri.parse('https://ui.adsabs.harvard.edu/user/settings/token');
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      throw Exception('Could not launch NASA ADS token page');
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SearchProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Configuración ⚙️'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // NASA ADS API Section
          const Text(
            '🚀 NASA ADS API Token (Gratuito)',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          const Text(
            'Ingresa tu token gratuito de NASA ADS para buscar conteo de citas y descargar citas oficiales.',
            style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8)),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _adsKeyCtrl,
            obscureText: true,
            decoration: const InputDecoration(
              hintText: 'Pega tu Token de NASA ADS aquí...',
              filled: true,
              fillColor: Color(0xFF1E293B),
              border: OutlineInputBorder(borderRadius: BorderRadius.all(Radius.circular(12))),
            ),
            onChanged: (val) => provider.setAdsApiKey(val),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF38BDF8), foregroundColor: Colors.black),
                icon: const Icon(Icons.check_circle_outline, size: 18),
                label: const Text('Verificar Token'),
                onPressed: _isTestingToken ? null : _verifyAdsKey,
              ),
              const SizedBox(width: 8),
              TextButton.icon(
                icon: const Icon(Icons.open_in_new, size: 16),
                label: const Text('Obtener Token Gratis'),
                onPressed: _openNasaAdsTokenPage,
              ),
            ],
          ),
          if (_adsStatusMsg != null) ...[
            const SizedBox(height: 8),
            Text(
              _adsStatusMsg!,
              style: TextStyle(
                color: _adsStatusMsg!.startsWith('✅') ? Colors.greenAccent : Colors.redAccent,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],

          const Divider(height: 40, color: Color(0xFF334155)),

          // Local Storage Info Section
          const Text(
            '💾 Almacenamiento Local',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          const Text(
            'Los artículos y archivos PDF se descargan directamente en la carpeta de Descargas de tu dispositivo sin requerir cuentas ni servicios de terceros.',
            style: TextStyle(fontSize: 13, color: Color(0xFF94A3B8)),
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: const Row(
              children: [
                Icon(Icons.folder_special_rounded, color: Color(0xFF38BDF8), size: 28),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Descargas directas activadas a tu almacenamiento local.',
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
