import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/article.dart';

class ArxivService {
  static const String baseUrl = 'https://export.arxiv.org/api/query';
  static const String localBackendUrl = 'http://localhost:8000/api/search';

  Future<List<Article>> search({
    required String query,
    int maxResults = 50,
    String sortBy = 'submittedDate',
  }) async {
    final String rawUrl =
        '$baseUrl?search_query=$query&start=0&max_results=$maxResults&sortBy=$sortBy&sortOrder=descending';

    if (kIsWeb) {
      // 1. Direct Request (works if browser allows or pre-cached)
      try {
        final response = await http.get(Uri.parse(rawUrl)).timeout(const Duration(seconds: 8));
        if (response.statusCode == 200 && response.body.contains('<entry>')) {
          final articles = _parseAtomXml(response.body);
          if (articles.isNotEmpty) return articles;
        }
      } catch (_) {}

      // 2. AllOrigins RAW Proxy
      try {
        final Uri proxyUrl = Uri.parse(
            'https://api.allorigins.win/raw?url=${Uri.encodeComponent(rawUrl)}');
        final response = await http.get(proxyUrl).timeout(const Duration(seconds: 10));
        if (response.statusCode == 200 && response.body.contains('<entry>')) {
          final articles = _parseAtomXml(response.body);
          if (articles.isNotEmpty) return articles;
        }
      } catch (_) {}

      // 3. CodeTabs CORS Proxy
      try {
        final Uri proxyUrl = Uri.parse(
            'https://api.codetabs.com/v1/proxy?quest=${Uri.encodeComponent(rawUrl)}');
        final response = await http.get(proxyUrl).timeout(const Duration(seconds: 10));
        if (response.statusCode == 200 && response.body.contains('<entry>')) {
          final articles = _parseAtomXml(response.body);
          if (articles.isNotEmpty) return articles;
        }
      } catch (_) {}

      // 4. CrossRef Open Scientific Search Fallback (Native Web CORS support)
      try {
        final Uri crossrefUrl = Uri.parse(
            'https://api.crossref.org/works?query=${Uri.encodeComponent(query)}&rows=$maxResults');
        final response = await http.get(crossrefUrl).timeout(const Duration(seconds: 10));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final items = data['message']?['items'] as List?;
          if (items != null && items.isNotEmpty) {
            final List<Article> articles = [];
            for (final item in items) {
              final titleList = item['title'] as List?;
              final title = titleList != null && titleList.isNotEmpty ? titleList.first.toString() : 'Sin título';
              
              final authorList = item['author'] as List?;
              final List<String> authors = [];
              if (authorList != null) {
                for (final a in authorList) {
                  final given = a['given'] ?? '';
                  final family = a['family'] ?? '';
                  final name = '$given $family'.trim();
                  if (name.isNotEmpty) authors.add(name);
                }
              }

              final doi = item['DOI']?.toString();
              final yearParts = item['issued']?['date-parts'] as List?;
              String pubDate = '';
              if (yearParts != null && yearParts.isNotEmpty && yearParts.first is List) {
                final year = yearParts.first.first;
                if (year != null) pubDate = year.toString();
              }

              final abstractXml = item['abstract']?.toString() ?? '';
              final abstractText = abstractXml.replaceAll(RegExp(r'<[^>]*>'), '').trim();

              final linkUrl = item['URL']?.toString() ?? (doi != null ? 'https://doi.org/$doi' : null);

              articles.add(Article(
                id: doi != null ? 'crossref_$doi' : 'arxiv_${articles.length}',
                title: title,
                authors: authors.isEmpty ? ['Autor desconocido'] : authors,
                abstractText: abstractText.isEmpty ? 'Resumen no disponible para este artículo.' : abstractText,
                pubDate: pubDate,
                source: 'arXiv / CrossRef',
                doi: doi,
                pdfUrl: linkUrl,
                url: linkUrl,
                citations: item['is-referenced-by-count'] as int? ?? 0,
              ));
            }
            if (articles.isNotEmpty) return articles;
          }
        }
      } catch (_) {}

      throw Exception('No se pudo conectar con los servidores de arXiv / Literatura científica en Web.');
    }

    // Direct request for Native platforms (iOS, Android, macOS)
    try {
      final response = await http.get(Uri.parse(rawUrl)).timeout(const Duration(seconds: 25));
      if (response.statusCode == 200) {
        return _parseAtomXml(response.body);
      } else {
        throw Exception('Error al conectar con arXiv API (HTTP ${response.statusCode})');
      }
    } catch (e) {
      throw Exception('Error al realizar búsqueda en arXiv: $e');
    }
  }

  List<Article> _parseAtomXml(String xmlStr) {
    final List<Article> articles = [];
    final entryRegExp = RegExp(r'<entry>(.*?)</entry>', dotAll: true);
    final matches = entryRegExp.allMatches(xmlStr);

    for (final match in matches) {
      final entryContent = match.group(1) ?? '';
      
      final idMatch = RegExp(r'<id>(.*?)</id>').firstMatch(entryContent);
      final rawId = idMatch?.group(1)?.trim() ?? '';
      final arxivId = rawId.split('/abs/').last.replaceAll(RegExp(r'v\d+$'), '');

      final titleMatch = RegExp(r'<title>(.*?)</title>', dotAll: true).firstMatch(entryContent);
      final title = (titleMatch?.group(1) ?? 'Sin título')
          .replaceAll('\n', ' ')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();

      final summaryMatch = RegExp(r'<summary>(.*?)</summary>', dotAll: true).firstMatch(entryContent);
      final abstractText = (summaryMatch?.group(1) ?? 'Sin resumen disponible.')
          .replaceAll('\n', ' ')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();

      final publishedMatch = RegExp(r'<published>(.*?)</published>').firstMatch(entryContent);
      final pubDateStr = publishedMatch?.group(1) ?? '';
      final pubDate = pubDateStr.length >= 7 ? pubDateStr.substring(0, 7) : pubDateStr;

      final authorMatches = RegExp(r'<author>\s*<name>(.*?)</name>\s*</author>', dotAll: true).allMatches(entryContent);
      final authors = authorMatches.map((m) => m.group(1)!.trim()).toList();

      final doiMatch = RegExp(r'<arxiv:doi.*?>(.*?)</arxiv:doi>').firstMatch(entryContent);
      final doi = doiMatch?.group(1)?.trim();

      articles.add(Article(
        id: 'arxiv_$arxivId',
        title: title,
        authors: authors,
        abstractText: abstractText,
        pubDate: pubDate,
        source: 'arXiv',
        arxivId: arxivId,
        doi: doi,
        pdfUrl: 'https://arxiv.org/pdf/$arxivId.pdf',
        url: 'https://arxiv.org/abs/$arxivId',
        citations: 0,
      ));
    }

    return articles;
  }
}
