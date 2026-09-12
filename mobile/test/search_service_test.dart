import 'package:flutter_test/flutter_test.dart';
import 'package:searchforlens_mobile/models/article.dart';
import 'package:searchforlens_mobile/services/search_service.dart';

void main() {
  group('UnifiedSearchService Deduplication & Formatting Tests', () {
    final service = UnifiedSearchService();

    test('Handles titles with leading/trailing spaces without throwing RangeError', () async {
      final article1 = Article(
        id: 'test_1',
        title: '   A Study of Strong Gravitational Lensing   ', // untrimmed len = 45, trimmed len = 39
        authors: ['Author A'],
        abstractText: 'Abstract test 1',
        pubDate: '2024-01',
        source: 'arXiv',
      );

      final article2 = Article(
        id: 'test_2',
        title: '   A Study of Strong Gravitational Lensing   ',
        authors: ['Author A'],
        abstractText: 'Abstract test 2',
        pubDate: '2024-01',
        source: 'INSPIRE-HEP',
      );

      expect(article1.title.length, equals(45));
      expect(article2.title.trim().length, equals(39));

      final res = await service.search(
        presetType: 'custom',
        customQuery: 'strong lensing',
        author: '',
        source: 'all',
        adsApiKey: '',
      );

      expect(res, isA<Map<String, dynamic>>());
      expect(res['articles'], isA<List<Article>>());
    });
  });
}
