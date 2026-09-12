import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/article.dart';

class InspireService {
  static const String baseUrl = 'https://inspirehep.net/api/literature';
  static const String localBackendUrl = 'http://localhost:8000/api/search';

  Future<List<Article>> search({
    required String query,
    int maxResults = 50,
    String sortBy = 'date',
  }) async {
    if (kIsWeb) {
      try {
        final Uri url = Uri.parse(
            '$localBackendUrl?preset_type=custom&custom_query=${Uri.encodeComponent(query)}&max_results=$maxResults&source=inspire');
        final response = await http.get(url).timeout(const Duration(seconds: 4));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final List articlesJson = data['articles'] ?? [];
          if (articlesJson.isNotEmpty) {
            return articlesJson
                .map((j) => Article.fromJson(Map<String, dynamic>.from(j)))
                .toList();
          }
        }
      } catch (_) {}
    }

    String sortOrder = 'mostrecent';
    if (sortBy == 'citations') sortOrder = 'mostcited';

    final Uri url = Uri.parse(
        '$baseUrl?q=${Uri.encodeComponent(query)}&size=$maxResults&sort=$sortOrder');

    try {
      final response = await http.get(url).timeout(const Duration(seconds: 15));
      if (response.statusCode != 200) {
        throw Exception('Error al conectar con INSPIRE-HEP (HTTP ${response.statusCode})');
      }

      final data = jsonDecode(response.body);
      final List hits = data['hits']?['hits'] ?? [];
      final List<Article> articles = [];

      for (final hit in hits) {
        final id = hit['id']?.toString() ?? '';
        final metadata = hit['metadata'] ?? {};

        final titles = metadata['titles'] as List?;
        final title = titles != null && titles.isNotEmpty ? (titles[0]['title'] ?? 'Sin título') : 'Sin título';

        final abstracts = metadata['abstracts'] as List?;
        final abstractText = abstracts != null && abstracts.isNotEmpty
            ? (abstracts[0]['value'] ?? 'Sin resumen disponible.')
            : 'Sin resumen disponible.';

        final authorsList = metadata['authors'] as List?;
        final authors = <String>[];
        if (authorsList != null) {
          for (final a in authorsList) {
            final name = a['full_name'] ?? a['first_name'] ?? 'Autor';
            authors.add(name);
          }
        }

        final pubDate = metadata['earliest_date'] ?? metadata['publication_info']?[0]?['year']?.toString() ?? '';
        final citations = metadata['citation_count'] ?? 0;

        String? arxivId;
        final arxivs = metadata['arxiv_eprints'] as List?;
        if (arxivs != null && arxivs.isNotEmpty) {
          arxivId = arxivs[0]['value'];
        }

        String? doi;
        final dois = metadata['dois'] as List?;
        if (dois != null && dois.isNotEmpty) {
          doi = dois[0]['value'];
        }

        final pdfUrl = arxivId != null ? 'https://arxiv.org/pdf/$arxivId.pdf' : null;

        articles.add(Article(
          id: 'inspire_$id',
          title: title,
          authors: authors,
          abstractText: abstractText,
          pubDate: pubDate.length >= 7 ? pubDate.substring(0, 7) : pubDate,
          source: 'INSPIRE-HEP',
          arxivId: arxivId,
          inspireId: id,
          doi: doi,
          pdfUrl: pdfUrl,
          url: 'https://inspirehep.net/literature/$id',
          citations: citations,
        ));
      }

      return articles;
    } catch (e) {
      throw Exception('Error al consultar INSPIRE-HEP: $e');
    }
  }
}
