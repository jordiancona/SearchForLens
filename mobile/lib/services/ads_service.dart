import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/article.dart';

class AdsService {
  static const String searchUrl = 'https://api.adsabs.harvard.edu/v1/search/query';
  static const String bibtexUrl = 'https://api.adsabs.harvard.edu/v1/export/bibtex';
  static const String localBackendUrl = 'http://localhost:8000/api/search';

  Future<bool> verifyApiKey(String token) async {
    final cleanToken = token.trim();
    if (cleanToken.isEmpty) return false;

    if (kIsWeb) {
      // 1. Try local Python backend
      try {
        final Uri url = Uri.parse(
            '$localBackendUrl?preset_type=custom&custom_query=star&max_results=1&ads_api_key=${Uri.encodeComponent(cleanToken)}&source=ads');
        final response = await http.get(url).timeout(const Duration(seconds: 4));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final List errors = data['errors'] ?? [];
          final bool hasAdsError = errors.any((e) => e.toString().toLowerCase().contains('ads'));
          return !hasAdsError;
        }
      } catch (_) {}

      // 2. Try Web Proxy for production (GitHub Pages)
      try {
        final String rawUrl = '$searchUrl?q=star&rows=1&fl=id';
        final Uri proxyUrl = Uri.parse('https://api.allorigins.win/get?url=${Uri.encodeComponent(rawUrl)}');
        final response = await http.get(
          proxyUrl,
          headers: {'Authorization': 'Bearer $cleanToken'},
        ).timeout(const Duration(seconds: 8));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final contents = data['contents'] as String?;
          if (contents != null && (contents.contains('"docs"') || contents.contains('"numFound"'))) {
            return true;
          }
        }
      } catch (_) {}

      return false;
    }

    // Direct call for Native platforms (iOS, Android, macOS desktop)
    try {
      final response = await http.get(
        Uri.parse('$searchUrl?q=star&rows=1&fl=id'),
        headers: {'Authorization': 'Bearer $cleanToken'},
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
    final cleanKey = apiKey.trim();
    if (cleanKey.isEmpty) {
      throw Exception('Se requiere una API Key de NASA ADS configurada en Ajustes.');
    }

    if (kIsWeb) {
      // 1. Try Local Backend
      try {
        final Uri url = Uri.parse(
            '$localBackendUrl?preset_type=custom&custom_query=${Uri.encodeComponent(query)}&max_results=$rows&ads_api_key=${Uri.encodeComponent(cleanKey)}&source=ads');
        final response = await http.get(url).timeout(const Duration(seconds: 4));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final List errors = data['errors'] ?? [];
          final bool hasAdsError = errors.any((e) => e.toString().toLowerCase().contains('ads'));
          if (hasAdsError) {
            final adsErr = errors.firstWhere((e) => e.toString().toLowerCase().contains('ads'));
            throw Exception(adsErr.toString());
          }
          final List articlesJson = data['articles'] ?? [];
          return articlesJson
              .map((j) => Article.fromJson(Map<String, dynamic>.from(j)))
              .toList();
        }
      } catch (e) {
        if (e.toString().contains('NASA ADS:')) rethrow;
      }

      // 2. Try AllOrigins Web Proxy for GitHub Pages
      try {
        final String rawUrl =
            '$searchUrl?q=${Uri.encodeComponent(query)}&fl=id,bibcode,title,author,abstract,pubdate,citation_count,doi,identifier,pub,eprint&rows=$rows&sort=$sort';
        final Uri proxyUrl = Uri.parse('https://api.allorigins.win/get?url=${Uri.encodeComponent(rawUrl)}');
        final response = await http.get(proxyUrl).timeout(const Duration(seconds: 12));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final contents = data['contents'] as String?;
          if (contents != null && contents.isNotEmpty) {
            final parsed = jsonDecode(contents);
            if (parsed['response'] != null) {
              return _parseDocs(parsed);
            }
          }
        }
      } catch (_) {}

      throw Exception(
          'Para consultar NASA ADS en desarrollo Web, inicia el servidor backend ejecutando "python server.py" en la terminal.');
    }

    // Direct call for Native platforms
    final Uri url = Uri.parse(
        '$searchUrl?q=${Uri.encodeComponent(query)}&fl=id,bibcode,title,author,abstract,pubdate,citation_count,doi,identifier,pub,eprint&rows=$rows&sort=$sort');

    final response = await http.get(
      url,
      headers: {'Authorization': 'Bearer $cleanKey'},
    ).timeout(const Duration(seconds: 15));

    if (response.statusCode == 401) {
      throw Exception('API Key de NASA ADS inválida. Verifique sus credenciales.');
    } else if (response.statusCode != 200) {
      throw Exception('Respuesta inesperada de NASA ADS (Código ${response.statusCode})');
    }

    return _parseDocs(jsonDecode(response.body));
  }

  List<Article> _parseDocs(Map<String, dynamic> data) {
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
  }

  Future<String?> fetchBibtex(String apiKey, String bibcode) async {
    final cleanKey = apiKey.trim();
    if (cleanKey.isEmpty || bibcode.isEmpty) return null;

    if (kIsWeb) {
      try {
        final Uri url = Uri.parse(
            '$localBackendUrl?preset_type=custom&custom_query=$bibcode&max_results=1&ads_api_key=${Uri.encodeComponent(cleanKey)}&source=ads');
        final response = await http.get(url).timeout(const Duration(seconds: 4));
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          final List articlesJson = data['articles'] ?? [];
          if (articlesJson.isNotEmpty) {
            return Article.fromJson(articlesJson[0]).generateBibtex();
          }
        }
      } catch (_) {}
    }

    try {
      final response = await http.post(
        Uri.parse(bibtexUrl),
        headers: {
          'Authorization': 'Bearer $cleanKey',
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
