class Article {
  final String id;
  final String title;
  final List<String> authors;
  final String abstractText;
  final String pubDate;
  String source;
  final String? arxivId;
  final String? bibcode;
  final String? inspireId;
  final String? doi;
  final String? pdfUrl;
  final String? url;
  int citations;
  final String? journal;
  final String? rawBibtex;

  Article({
    required this.id,
    required this.title,
    required this.authors,
    required this.abstractText,
    required this.pubDate,
    required this.source,
    this.arxivId,
    this.bibcode,
    this.inspireId,
    this.doi,
    this.pdfUrl,
    this.url,
    this.citations = 0,
    this.journal,
    this.rawBibtex,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'authors': authors,
        'abstract': abstractText,
        'pub_date': pubDate,
        'source': source,
        'arxiv_id': arxivId,
        'bibcode': bibcode,
        'inspire_id': inspireId,
        'doi': doi,
        'pdf_url': pdfUrl,
        'url': url,
        'citations': citations,
        'journal': journal,
        'raw_bibtex': rawBibtex,
      };

  factory Article.fromJson(Map<String, dynamic> json) => Article(
        id: json['id'] ?? '',
        title: json['title'] ?? 'Sin título',
        authors: List<String>.from(json['authors'] ?? []),
        abstractText: json['abstract'] ?? 'Sin resumen disponible.',
        pubDate: json['pub_date'] ?? '',
        source: json['source'] ?? 'Unknown',
        arxivId: json['arxiv_id'],
        bibcode: json['bibcode'],
        inspireId: json['inspire_id'],
        doi: json['doi'],
        pdfUrl: json['pdf_url'],
        url: json['url'],
        citations: json['citations'] ?? 0,
        journal: json['journal'],
        rawBibtex: json['raw_bibtex'],
      );

  String generateBibtex() {
    if (rawBibtex != null && rawBibtex!.isNotEmpty) {
      return rawBibtex!;
    }
    final firstAuthor = authors.isNotEmpty ? authors[0].split(' ').last : 'Author';
    final year = pubDate.length >= 4 ? pubDate.substring(0, 4) : '2026';
    final key = '$firstAuthor$year${id.replaceAll('/', '_').replaceAll('.', '_')}';
    final authorsStr = authors.join(' and ');

    final buffer = StringBuffer();
    buffer.writeln('@article{$key,');
    buffer.writeln('  title = {$title},');
    buffer.writeln('  author = {$authorsStr},');
    buffer.writeln('  year = {$year},');
    if (journal != null && journal!.isNotEmpty) {
      buffer.writeln('  journal = {$journal},');
    }
    if (arxivId != null && arxivId!.isNotEmpty) {
      buffer.writeln('  eprint = {$arxivId},');
      buffer.writeln('  archivePrefix = {arXiv},');
    }
    if (doi != null && doi!.isNotEmpty) {
      buffer.writeln('  doi = {$doi},');
    }
    if (url != null && url!.isNotEmpty) {
      buffer.writeln('  url = {$url},');
    }
    buffer.write('}');
    return buffer.toString();
  }
}
