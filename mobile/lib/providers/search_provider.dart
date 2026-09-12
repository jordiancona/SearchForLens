import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/article.dart';
import '../services/google_drive_service.dart';
import '../services/search_service.dart';
import '../services/zotero_service.dart';

class SearchProvider with ChangeNotifier {
  final UnifiedSearchService _searchService = UnifiedSearchService();

  String _adsApiKey = '';
  String _googleClientId = '';
  String _googleUserEmail = '';
  String _zoteroUserId = '';
  String _zoteroApiKey = '';
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
  String get googleUserEmail => _googleUserEmail;
  String get zoteroUserId => _zoteroUserId;
  String get zoteroApiKey => _zoteroApiKey;
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
    _googleUserEmail = prefs.getString('google_user_email') ?? '';
    _zoteroUserId = prefs.getString('zotero_user_id') ?? '';
    _zoteroApiKey = prefs.getString('zotero_api_key') ?? '';
    
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

  Future<void> setZoteroUserId(String id) async {
    _zoteroUserId = id.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('zotero_user_id', _zoteroUserId);
    notifyListeners();
  }

  Future<void> setZoteroApiKey(String key) async {
    _zoteroApiKey = key.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('zotero_api_key', _zoteroApiKey);
    notifyListeners();
  }

  Future<void> setGoogleClientId(String id) async {
    _googleClientId = id.trim();
    _googleSignInInstance = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('google_client_id', _googleClientId);
    notifyListeners();
  }

  Future<void> setGoogleUserEmail(String email) async {
    _googleUserEmail = email.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('google_user_email', _googleUserEmail);
    notifyListeners();
  }

  GoogleSignInAccount? _googleAccount;
  GoogleSignInAccount? get googleAccount => _googleAccount;

  GoogleSignIn? _googleSignInInstance;

  GoogleSignIn _getGoogleSignIn() {
    if (_googleSignInInstance != null) return _googleSignInInstance!;
    final String? clientId = _googleClientId.trim().isNotEmpty ? _googleClientId.trim() : null;
    _googleSignInInstance = GoogleSignIn(
      clientId: clientId,
      scopes: [
        'email',
        'https://www.googleapis.com/auth/drive.file',
      ],
    );
    return _googleSignInInstance!;
  }

  Future<bool> signInWithGoogle() async {
    try {
      final googleSignIn = _getGoogleSignIn();
      final account = await googleSignIn.signIn();
      if (account != null) {
        _googleAccount = account;
        _googleUserEmail = account.email;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('google_user_email', _googleUserEmail);
        notifyListeners();
        return true;
      }
    } catch (e) {
      debugPrint('Google Sign-In Error: $e');
      rethrow;
    }
    return false;
  }

  Future<void> signOutGoogle() async {
    try {
      final googleSignIn = _getGoogleSignIn();
      await googleSignIn.signOut();
    } catch (e) {
      debugPrint('Google Sign-Out Error: $e');
    }
    _googleAccount = null;
    _googleUserEmail = '';
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('google_user_email');
    notifyListeners();
  }

  Future<bool> uploadArticleToDrive(Article article) async {
    final googleSignIn = _getGoogleSignIn();

    if (_googleAccount == null) {
      try {
        _googleAccount = await googleSignIn.signInSilently();
      } catch (_) {}
    }

    if (_googleAccount == null) {
      _googleAccount = await googleSignIn.signIn();
      if (_googleAccount != null) {
        _googleUserEmail = _googleAccount!.email;
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('google_user_email', _googleUserEmail);
        notifyListeners();
      }
    }

    if (_googleAccount == null) {
      throw Exception('Por favor inicia sesión con tu cuenta de Google.');
    }

    return await GoogleDriveService.uploadArticlePdfToDrive(
      account: _googleAccount!,
      article: article,
    );
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

  Future<bool> uploadArticleToZotero(Article article) async {
    if (_zoteroUserId.isEmpty || _zoteroApiKey.isEmpty) {
      throw Exception('Por favor configura tu User ID y API Key de Zotero en Ajustes.');
    }

    return await ZoteroService.createItem(
      userId: _zoteroUserId,
      apiKey: _zoteroApiKey,
      article: article,
    );
  }

  Future<int> exportArticlesToZotero(List<Article> articles) async {
    if (_zoteroUserId.isEmpty || _zoteroApiKey.isEmpty) {
      throw Exception('Por favor configura tu User ID y API Key de Zotero en Ajustes.');
    }

    return await ZoteroService.createItemsBatch(
      userId: _zoteroUserId,
      apiKey: _zoteroApiKey,
      articles: articles,
    );
  }
}
