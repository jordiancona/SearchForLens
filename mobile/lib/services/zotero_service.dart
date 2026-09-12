import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/article.dart';

class ZoteroService {
  static const String baseUrl = 'https://api.zotero.org';

  static Future<bool> verifyCredentials(String userId, String apiKey) async {
    final uid = userId.trim();
    final key = apiKey.trim();

    if (uid.isEmpty || key.isEmpty) return false;

    final Uri url = Uri.parse('$baseUrl/users/$uid/items?limit=1');
    try {
      final response = await http.get(
        url,
        headers: {
          'Zotero-API-Key': key,
          'Zotero-API-Version': '3',
        },
      ).timeout(const Duration(seconds: 8));

      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Map<String, dynamic> articleToZoteroItem(Article article) {
    final List<Map<String, dynamic>> creators = [];

    for (final author in article.authors) {
      final clean = author.trim();
      final parts = clean.split(' ');
      if (parts.length > 1) {
        creators.add({
          'creatorType': 'author',
          'firstName': parts.sublist(0, parts.length - 1).join(' '),
          'lastName': parts.last,
        });
      } else if (clean.isNotEmpty) {
        creators.add({
          'creatorType': 'author',
          'name': clean,
        });
      }
    }

    if (creators.isEmpty) {
      creators.add({'creatorType': 'author', 'name': 'Autor Desconocido'});
    }

    final year = article.pubDate.length >= 4 ? article.pubDate.substring(0, 4) : '';

    final List<String> extraLines = [];
    if (article.arxivId != null && article.arxivId!.isNotEmpty) {
      extraLines.add('arXiv: ${article.arxivId}');
    }
    if (article.bibcode != null && article.bibcode!.isNotEmpty) {
      extraLines.add('Bibcode: ${article.bibcode}');
    }
    if (article.inspireId != null && article.inspireId!.isNotEmpty) {
      extraLines.add('INSPIRE: ${article.inspireId}');
    }
    if (article.citations > 0) {
      extraLines.add('Citations: ${article.citations}');
    }

    return {
      'itemType': 'journalArticle',
      'title': article.title,
      'creators': creators,
      'abstractNote': article.abstractText,
      'publicationTitle': article.journal ?? 'Preprint (${article.source})',
      'date': year,
      'DOI': article.doi ?? '',
      'url': article.url ?? article.pdfUrl ?? '',
      'extra': extraLines.join('\n'),
    };
  }

  static Future<bool> createItem({
    required String userId,
    required String apiKey,
    required Article article,
  }) async {
    final uid = userId.trim();
    final key = apiKey.trim();

    if (uid.isEmpty || key.isEmpty) {
      throw Exception('Por favor configura tu User ID y API Key de Zotero en Ajustes.');
    }

    final Uri url = Uri.parse('$baseUrl/users/$uid/items');
    final itemData = articleToZoteroItem(article);

    final response = await http.post(
      url,
      headers: {
        'Zotero-API-Key': key,
        'Zotero-API-Version': '3',
        'Content-Type': 'application/json',
      },
      body: jsonEncode([itemData]),
    ).timeout(const Duration(seconds: 12));

    if (response.statusCode == 200 || response.statusCode == 201) {
      return true;
    } else {
      throw Exception('Error al guardar en Zotero (HTTP ${response.statusCode})');
    }
  }

  static Future<int> createItemsBatch({
    required String userId,
    required String apiKey,
    required List<Article> articles,
  }) async {
    final uid = userId.trim();
    final key = apiKey.trim();

    if (uid.isEmpty || key.isEmpty) {
      throw Exception('Por favor configura tu User ID y API Key de Zotero en Ajustes.');
    }

    if (articles.isEmpty) return 0;

    final Uri url = Uri.parse('$baseUrl/users/$uid/items');
    const int batchSize = 50;
    int successCount = 0;

    for (int i = 0; i < articles.length; i += batchSize) {
      final end = (i + batchSize < articles.length) ? i + batchSize : articles.length;
      final batch = articles.sublist(i, end);
      final payload = batch.map((a) => articleToZoteroItem(a)).toList();

      final response = await http.post(
        url,
        headers: {
          'Zotero-API-Key': key,
          'Zotero-API-Version': '3',
          'Content-Type': 'application/json',
        },
        body: jsonEncode(payload),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = jsonDecode(response.body);
        final Map? succ = data['success'] as Map?;
        successCount += succ?.length ?? batch.length;
      } else {
        throw Exception('Error en lote de Zotero (HTTP ${response.statusCode})');
      }
    }

    return successCount;
  }
}
