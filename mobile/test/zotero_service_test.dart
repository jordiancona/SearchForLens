import 'package:flutter_test/flutter_test.dart';
import 'package:searchforlens_mobile/models/article.dart';
import 'package:searchforlens_mobile/services/zotero_service.dart';

void main() {
  group('ZoteroService Tests', () {
    test('articleToZoteroItem converts Article to Zotero journalArticle schema', () {
      final article = Article(
        id: 'arxiv_2401.00001',
        title: 'Gravitational Lensing Research',
        authors: ['John Doe', 'Jane Smith'],
        abstractText: 'Abstract content',
        pubDate: '2024-03-10',
        source: 'arXiv',
        arxivId: '2401.00001',
        doi: '10.1000/test.doi',
        citations: 15,
        journal: 'Monthly Notices of the Royal Astronomical Society',
      );

      final item = ZoteroService.articleToZoteroItem(article);

      expect(item['itemType'], equals('journalArticle'));
      expect(item['title'], equals('Gravitational Lensing Research'));
      expect(item['publicationTitle'], equals('Monthly Notices of the Royal Astronomical Society'));
      expect(item['date'], equals('2024'));
      expect(item['DOI'], equals('10.1000/test.doi'));

      final creators = item['creators'] as List;
      expect(creators.length, equals(2));
      expect(creators[0]['firstName'], equals('John'));
      expect(creators[0]['lastName'], equals('Doe'));
    });
  });
}
