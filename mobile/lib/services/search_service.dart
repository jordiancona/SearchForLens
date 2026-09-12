import '../models/article.dart';
import 'arxiv_service.dart';
import 'ads_service.dart';
import 'inspire_service.dart';

class UnifiedSearchService {
  final ArxivService _arxivService = ArxivService();
  final AdsService _adsService = AdsService();
  final InspireService _inspireService = InspireService();

  Future<Map<String, dynamic>> search({
    required String presetType,
    required String customQuery,
    required String author,
    int? startYear,
    int? endYear,
    required String source,
    required String adsApiKey,
    int maxResults = 50,
    String sortBy = 'date',
  }) async {
    final List<Article> allArticles = [];
    final List<String> errors = [];

    final bool queryArxiv = source == 'all' || source == 'arxiv' || source == 'both';
    final bool queryAds = source == 'all' || source == 'ads' || source == 'both';
    final bool queryInspire = source == 'all' || source == 'inspire' || source == 'both';

    // 1. ArXiv Query
    if (queryArxiv) {
      try {
        final q = _buildArxivQuery(presetType, customQuery, author);
        final results = await _arxivService.search(
          query: q,
          maxResults: maxResults,
          sortBy: sortBy == 'date' ? 'submittedDate' : 'relevance',
        );
        allArticles.addAll(results);
      } catch (e) {
        errors.add('arXiv: $e');
      }
    }

    // 2. NASA ADS Query
    if (queryAds) {
      if (adsApiKey.isEmpty) {
        errors.add('NASA ADS: Configura tu API Key gratuita en Ajustes.');
      } else {
        try {
          final q = _buildAdsQuery(presetType, customQuery, author, startYear, endYear);
          String sortParam = 'date desc';
          if (sortBy == 'citations') sortParam = 'citation_count desc';
          if (sortBy == 'relevance') sortParam = 'score desc';

          final results = await _adsService.search(
            apiKey: adsApiKey,
            query: q,
            rows: maxResults,
            sort: sortParam,
          );
          allArticles.addAll(results);
        } catch (e) {
          errors.add('NASA ADS: $e');
        }
      }
    }

    // 3. INSPIRE-HEP Query
    if (queryInspire) {
      try {
        final q = _buildInspireQuery(presetType, customQuery, author);
        final results = await _inspireService.search(
          query: q,
          maxResults: maxResults,
          sortBy: sortBy,
        );
        allArticles.addAll(results);
      } catch (e) {
        errors.add('INSPIRE-HEP: $e');
      }
    }

    // Deduplicate & Process
    List<Article> merged = allArticles;
    try {
      merged = _deduplicate(allArticles);

      // Filter by year
      if (startYear != null || endYear != null) {
        merged = _filterByYear(merged, startYear, endYear);
      }

      // Sort
      merged = _sortArticles(merged, sortBy);
    } catch (e) {
      errors.add('Procesamiento de resultados: $e');
    }

    final sourcesUsed = <String>[];
    if (queryArxiv) sourcesUsed.add('arXiv');
    if (queryAds) sourcesUsed.add('NASA ADS');
    if (queryInspire) sourcesUsed.add('INSPIRE-HEP');

    return {
      'articles': merged,
      'errors': errors,
      'source_summary': sourcesUsed.join(' + '),
    };
  }

  List<Article> _deduplicate(List<Article> articles) {
    final Map<String, Article> uniqueMap = {};
    final Map<String, Set<String>> sourceTracker = {};

    for (final article in articles) {
      String key;
      if (article.arxivId != null && article.arxivId!.isNotEmpty) {
        key = 'arxiv:${article.arxivId!.split('v')[0].toLowerCase()}';
      } else if (article.bibcode != null && article.bibcode!.isNotEmpty) {
        key = 'bibcode:${article.bibcode!.toLowerCase()}';
      } else if (article.doi != null && article.doi!.isNotEmpty) {
        key = 'doi:${article.doi!.toLowerCase()}';
      } else if (article.inspireId != null && article.inspireId!.isNotEmpty) {
        key = 'inspire:${article.inspireId!}';
      } else {
        final cleanTitle = article.title.trim().toLowerCase();
        final maxLen = cleanTitle.length > 50 ? 50 : cleanTitle.length;
        key = 'title:${cleanTitle.substring(0, maxLen)}';
      }

      if (!uniqueMap.containsKey(key)) {
        uniqueMap[key] = article;
        sourceTracker[key] = {article.source};
      } else {
        final existing = uniqueMap[key]!;
        sourceTracker[key]!.add(article.source);

        if (article.citations > existing.citations) {
          existing.citations = article.citations;
        }
      }
    }

    for (final entry in uniqueMap.entries) {
      final sources = sourceTracker[entry.key]!;
      if (sources.length > 1) {
        final ordered = <String>[];
        for (final s in ['arXiv', 'NASA ADS', 'INSPIRE-HEP']) {
          if (sources.contains(s)) ordered.add(s);
        }
        entry.value.source = ordered.join(' + ');
      }
    }

    return uniqueMap.values.toList();
  }

  List<Article> _filterByYear(List<Article> articles, int? startYear, int? endYear) {
    return articles.where((a) {
      if (a.pubDate.length < 4) return true;
      final year = int.tryParse(a.pubDate.substring(0, 4));
      if (year == null) return true;
      if (startYear != null && year < startYear) return false;
      if (endYear != null && year > endYear) return false;
      return true;
    }).toList();
  }

  List<Article> _sortArticles(List<Article> articles, String sortBy) {
    if (sortBy == 'citations') {
      articles.sort((a, b) => b.citations.compareTo(a.citations));
    } else if (sortBy == 'date') {
      articles.sort((a, b) => b.pubDate.compareTo(a.pubDate));
    }
    return articles;
  }

  String _buildArxivQuery(String preset, String custom, String author) {
    final terms = <String>[];
    if (preset == 'strong_lensing') {
      terms.add('ti:"strong gravitational lensing" OR abs:"strong gravitational lensing" OR ti:"strong lensing" OR abs:"strong lensing"');
    } else if (preset == 'ai_lensing') {
      terms.add('(ti:"gravitational lensing" OR abs:"gravitational lensing") AND (abs:"machine learning" OR abs:"deep learning" OR abs:"neural network" OR abs:"transformer" OR abs:"CNN")');
    } else if (custom.trim().isNotEmpty) {
      terms.add('ti:"${custom.trim()}" OR abs:"${custom.trim()}"');
    }

    if (author.trim().isNotEmpty) {
      terms.add('au:"${author.trim()}"');
    }

    return terms.isEmpty ? 'all:"gravitational lensing"' : terms.join(' AND ');
  }

  String _buildAdsQuery(String preset, String custom, String author, int? startYear, int? endYear) {
    final terms = <String>[];
    if (preset == 'strong_lensing') {
      terms.add('(title:("strong gravitational lensing" OR "strong lensing") OR abstract:("strong gravitational lensing" OR "strong lensing"))');
    } else if (preset == 'ai_lensing') {
      terms.add('(title:("gravitational lensing" OR "strong lensing") AND abstract:("machine learning" OR "deep learning" OR "neural network" OR "transformer"))');
    } else if (custom.trim().isNotEmpty) {
      terms.add('(title:"${custom.trim()}" OR abstract:"${custom.trim()}")');
    }

    if (author.trim().isNotEmpty) terms.add('author:"${author.trim()}"');
    if (startYear != null && endYear != null) terms.add('year:[$startYear TO $endYear]');
    return terms.isEmpty ? 'title:"gravitational lensing"' : terms.join(' AND ');
  }

  String _buildInspireQuery(String preset, String custom, String author) {
    if (preset == 'strong_lensing') return 'find t "strong gravitational lensing" or t "strong lensing"';
    if (preset == 'ai_lensing') return 'find t "gravitational lensing" and (t "machine learning" or t "deep learning" or t "neural network")';
    if (custom.trim().isNotEmpty) return 'find t ${custom.trim()}';
    if (author.trim().isNotEmpty) return 'find a ${author.trim()}';
    return 'find t "gravitational lensing"';
  }
}
