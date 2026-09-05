import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/article.dart';

class ArticleDetailModal extends StatelessWidget {
  final Article article;

  const ArticleDetailModal({super.key, required this.article});

  Future<void> _launchUrl(String urlStr) async {
    final Uri url = Uri.parse(urlStr);
    if (!await launchUrl(url, mode: LaunchMode.externalApplication)) {
      throw Exception('No se pudo abrir la URL: $urlStr');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: const BoxDecoration(
        color: Color(0xFF0F172A),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Handle bar
          Container(
            margin: const EdgeInsets.only(top: 12, bottom: 8),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: Colors.grey.shade600,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // Source Badges
                Row(
                  children: [
                    Chip(
                      backgroundColor: const Color(0xFF1E293B),
                      label: Text(
                        article.source,
                        style: const TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.bold),
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (article.citations > 0)
                      Chip(
                        backgroundColor: Colors.indigo.withOpacity(0.2),
                        label: Text(
                          '${article.citations} Citas',
                          style: const TextStyle(color: Colors.indigoAccent),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 12),

                // Title
                Text(
                  article.title,
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const SizedBox(height: 12),

                // Authors
                Text(
                  'Autores: ${article.authors.join(', ')}',
                  style: const TextStyle(fontSize: 14, color: Color(0xFF94A3B8)),
                ),
                const SizedBox(height: 16),

                // Action Buttons (PDF, Web, Drive)
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (article.pdf_url != null)
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0284C7)),
                        icon: const Icon(Icons.picture_as_pdf_rounded, size: 18),
                        label: const Text('Ver PDF'),
                        onPressed: () => _launchUrl(article.pdf_url!),
                      ),
                    if (article.url != null)
                      OutlinedButton.icon(
                        icon: const Icon(Icons.open_in_new_rounded, size: 18),
                        label: const Text('Enlace Oficial'),
                        onPressed: () => _launchUrl(article.url!),
                      ),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF059669)),
                      icon: const Icon(Icons.cloud_upload_rounded, size: 18),
                      label: const Text('☁️ PDF a Drive'),
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Guardando PDF en tu Google Drive personal...'),
                          ),
                        );
                      },
                    ),
                  ],
                ),
                const Divider(height: 32, color: Color(0xFF334155)),

                // Abstract Section
                const Text(
                  'Resumen',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const SizedBox(height: 8),
                Text(
                  article.abstractText,
                  style: const TextStyle(fontSize: 14, color: Color(0xFFCBD5E1), height: 1.5),
                ),
                const Divider(height: 32, color: Color(0xFF334155)),

                // BibTeX Section
                Row(
                  mainAxisAlignment: MainState.spaceBetween,
                  children: [
                    const Text(
                      'Cita en formato BibTeX',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    IconButton(
                      icon: const Icon(Icons.copy_rounded, color: Color(0xFF38BDF8)),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: article.generateBibtex()));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('¡BibTeX copiado al portapapeles!')),
                        );
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: SelectableText(
                    article.generateBibtex(),
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 12, color: Color(0xFF38BDF8)),
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
