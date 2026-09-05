import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/article.dart';
import '../services/search_service.dart';

class SearchProvider with ChangeNotifier {
  final UnifiedSearchService _searchService = UnifiedSearchService();

  String _adsApiKey = '';
  String _googleClientId = '';
  String _presetType = 'strong_lensing'; // 'strong_lensing', 'ai_lensing', 'custom'
  String _customQuery = '';
  String _author = '';
  int? _startYear;
  int? _endYear;
  String _source = 'all'; // 'all', 'arxiv', 'ads', 'inspire'
  String _sortBy = 'date'; // 'date', 'citations', 'relevance'

  bool _isLoading = false;
  String _statusMessage = '';
  String _sourceSummary = '';
  List<Article> _articles = [];
  List<Article> _favorites = [];
  List<String> _errors = [];

  // Getters
  String get adsApiKey => _adsApiKey;
  String get googleClientId => _googleClientId;
  String get presetType => _presetType;
  String get customQuery => _customQuery;
  String get author => _author;
  int? get startYear => _startYear;
  int? get endYear => _endYear;
  String get source => _source;
  String get sortBy => _sortBy;
  bool get isLoading => _isLoading;
  String get statusMessage => _statusMessage;
  String get sourceSummary => _sourceSummary;
  List<Article> get articles => _articles;
  List<Article> get favorites => _favorites;
  List<String> get errors => _errors;

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _adsApiKey = prefs.getString('ads_api_key') ?? '';
    _googleClientId = prefs.getString('google_client_id') ?? '';
    
    final favJson = prefs.getStringList('favorites') ?? [];
    _favorites = favJson.map((str) => Article.fromJson(jsonDecode(str))).toList();
    notifyListeners();
  }

  Future<void> setAdsApiKey(String key) async {
    _adsApiKey = key.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('ads_api_key', _adsApiKey);
    notifyListeners();
  }

  Future<void> setGoogleClientId(String id) async {
    _googleClientId = id.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('google_client_id', _googleClientId);
    notifyListeners();
  }

  void updateFilters({
    String? presetType,
    String? customQuery,
    String? author,
    int? startYear,
    int? endYear,
    String? source,
    String? sortBy,
  }) {
    if (presetType != null) _presetType = presetType;
    if (customQuery != null) _customQuery = customQuery;
    if (author != null) _author = author;
    _startYear = startYear;
    _endYear = endYear;
    if (source != null) _source = source;
    if (sortBy != null) _sortBy = sortBy;
    notifyListeners();
  }

  Future<void> performSearch() async {
    _isLoading = true;
    _statusMessage = 'Buscando artículos científicos...';
    _errors = [];
    notifyListeners();

    try {
      final res = await _searchService.search(
        presetType: _presetType,
        customQuery: _customQuery,
        author: _author,
        startYear: _startYear,
        endYear: _endYear,
        source: _source,
        adsApiKey: _adsApiKey,
        maxResults: 50,
        sortBy: _sortBy,
      );

      _articles = res['articles'];
      _errors = List<String>.from(res['errors']);
      _sourceSummary = res['source_summary'];
    } catch (e) {
      _errors.add(e.toString());
    } finally {
      _isLoading = false;
      _statusMessage = '';
      notifyListeners();
    }
  }

  bool isFavorite(String id) {
    return _favorites.any((a) => a.id == id);
  }

  Future<void> toggleFavorite(Article article) async {
    final index = _favorites.indexWhere((a) => a.id == article.id);
    if (index >= 0) {
      _favorites.removeAt(index);
    } else {
      _favorites.add(article);
    }

    final prefs = await SharedPreferences.getInstance();
    final favStrings = _favorites.map((a) => jsonEncode(a.toJson())).toList();
    await prefs.setStringList('favorites', favStrings);
    notifyListeners();
  }
}
