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
      // 1. Local Python Backend (fastest & bypasses all browser CORS/Cloudflare restrictions)
      try {
        final Uri backendUrl = Uri.parse(
            '$localBackendUrl?preset_type=custom&custom_query=${Uri.encodeComponent(query)}&max_results=$maxResults&source=arxiv');
        final response = await http.get(backendUrl).timeout(const Duration(seconds: 10));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final List articlesJson = data['articles'] ?? [];
          if (articlesJson.isNotEmpty) {
            return articlesJson.map((j) => Article.fromJson(j)).toList();
          }
        }
      } catch (_) {}

      // 2. AllOrigins JSON Proxy
      try {
        final Uri proxyUrl = Uri.parse(
            'https://api.allorigins.win/get?url=${Uri.encodeComponent(rawUrl)}');
        final response = await http.get(proxyUrl).timeout(const Duration(seconds: 15));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final xmlStr = data['contents'] as String?;
          if (xmlStr != null && xmlStr.isNotEmpty) {
            final articles = _parseAtomXml(xmlStr);
            if (articles.isNotEmpty) return articles;
          }
        }
      } catch (_) {}

      // 3. CorsProxy fallback
      try {
        final Uri proxyUrl = Uri.parse(
            'https://corsproxy.io/?${Uri.encodeComponent(rawUrl)}');
        final response = await http.get(proxyUrl).timeout(const Duration(seconds: 15));
        if (response.statusCode == 200 && response.body.isNotEmpty) {
          final articles = _parseAtomXml(response.body);
          if (articles.isNotEmpty) return articles;
        }
      } catch (_) {}

      throw Exception('No se pudo conectar con arXiv en Web.');
    }

    // Direct request for Native platforms (iOS, Android, macOS)
    try {
      final response = await http.get(Uri.parse(rawUrl)).timeout(const Duration(seconds: 15));
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
