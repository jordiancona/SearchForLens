import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/article.dart';

class AdsService {
  static const String searchUrl = 'https://api.adsabs.harvard.edu/v1/search/query';
  static const String bibtexUrl = 'https://api.adsabs.harvard.edu/v1/export/bibtex';

  Future<bool> verifyApiKey(String token) async {
    if (token.trim().isEmpty) return false;
    try {
      final response = await http.get(
        Uri.parse('$searchUrl?q=star&rows=1&fl=id'),
        headers: {'Authorization': 'Bearer ${token.trim()}'},
      ).timeout(const Duration(seconds: 10));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<Article>> search({
    required String apiKey,
    required String query,
    int rows = 50,
    String sort = 'date desc',
  }) async {
    if (apiKey.trim().isEmpty) {
      throw Exception('Se requiere una API Key de NASA ADS configurada en Ajustes.');
    }

    final Uri url = Uri.parse(
        '$searchUrl?q=${Uri.encodeComponent(query)}&fl=id,bibcode,title,author,abstract,pubdate,citation_count,doi,identifier,pub,eprint&rows=$rows&sort=$sort');

    try {
      final response = await http.get(
        url,
        headers: {'Authorization': 'Bearer ${apiKey.trim()}'},
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 401) {
        throw Exception('API Key de NASA ADS inválida. Verifique sus credenciales.');
      } else if (response.statusCode != 200) {
        throw Exception('Respuesta inesperada de NASA ADS (Código ${response.statusCode})');
      }

      final data = jsonDecode(response.body);
      final List docs = data['response']?['docs'] ?? [];
      final List<Article> articles = [];

      for (final doc in docs) {
        final bibcode = doc['bibcode'] ?? '';
        final titleList = doc['title'] ?? [];
        final title = titleList.isNotEmpty ? titleList[0] : 'Sin título';
        final abstractText = doc['abstract'] ?? 'Sin resumen disponible.';
        final authors = List<String>.from(doc['author'] ?? []);
        final pubdate = doc['pubdate'] ?? '';
        final pubDate = pubdate.length >= 7 ? pubdate.substring(0, 7) : (pubdate.length >= 4 ? pubdate.substring(0, 4) : '');
        final citations = doc['citation_count'] ?? 0;

        String? arxivId;
        String? doi;

        final eprint = doc['eprint']?.toString();
        if (eprint != null && eprint.isNotEmpty) {
          arxivId = _extractArxivId(eprint);
        }

        final identifiers = doc['identifier'] ?? [];
        for (final ident in identifiers) {
          final s = ident.toString();
          arxivId ??= _extractArxivId(s);
          if (s.contains('/') && s.contains('10.')) {
            doi ??= s;
          }
        }

        final doiList = doc['doi'] ?? [];
        if (doiList.isNotEmpty && doi == null) {
          doi = doiList[0];
        }

        final journal = doc['pub'] ?? 'NASA ADS';
        final pdfUrl = arxivId != null
            ? 'https://arxiv.org/pdf/$arxivId.pdf'
            : 'https://ui.adsabs.harvard.edu/abs/$bibcode/pdf';

        articles.add(Article(
          id: 'ads_$bibcode',
          title: title,
          authors: authors,
          abstractText: abstractText,
          pubDate: pubDate,
          source: 'NASA ADS',
          arxivId: arxivId,
          bibcode: bibcode,
          doi: doi,
          pdfUrl: pdfUrl,
          url: 'https://ui.adsabs.harvard.edu/abs/$bibcode/abstract',
          citations: citations,
          journal: journal,
        ));
      }

      return articles;
    } catch (e) {
      throw Exception('Error de red al consultar NASA ADS: $e');
    }
  }

  Future<String?> fetchBibtex(String apiKey, String bibcode) async {
    if (apiKey.isEmpty || bibcode.isEmpty) return null;
    try {
      final response = await http.post(
        Uri.parse(bibtexUrl),
        headers: {
          'Authorization': 'Bearer ${apiKey.trim()}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'bibcode': [bibcode]}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['export'];
      }
    } catch (_) {}
    return null;
  }

  String? _extractArxivId(String text) {
    final clean = text.replaceAll(RegExp(r'^arxiv:\s*', caseSensitive: false), '').trim();
    final reg = RegExp(r'(?:[a-zA-Z\-]+(?:\.[a-zA-Z]{2})?/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?');
    final match = reg.firstMatch(clean);
    return match?.group(0);
  }
}
