import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:googleapis/drive/v3.dart' as drive;
import 'package:http/http.dart' as http;
import '../models/article.dart';

class GoogleAuthClient extends http.BaseClient {
  final Map<String, String> _headers;
  final http.Client _client = http.Client();

  GoogleAuthClient(this._headers);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    request.headers.addAll(_headers);
    return _client.send(request);
  }
}

class GoogleDriveService {
  static Future<bool> uploadArticlePdfToDrive({
    required GoogleSignInAccount account,
    required Article article,
  }) async {
    try {
      Map<String, String> authHeaders = await account.authHeaders;
      if (!authHeaders.containsKey('Authorization')) {
        final auth = await account.authentication;
        if (auth.accessToken != null) {
          authHeaders = {
            'Authorization': 'Bearer ${auth.accessToken}',
          };
        }
      }

      final authenticateClient = GoogleAuthClient(authHeaders);
      final driveApi = drive.DriveApi(authenticateClient);

      List<int> fileBytes = [];
      bool isPdf = false;

      if (article.pdfUrl != null && article.pdfUrl!.isNotEmpty) {
        try {
          final res = await http.get(Uri.parse(article.pdfUrl!));
          if (res.statusCode == 200 && res.bodyBytes.isNotEmpty) {
            fileBytes = res.bodyBytes;
            isPdf = true;
          }
        } catch (e) {
          debugPrint('No se pudo descargar el PDF directamente por CORS/Red: $e');
        }
      }

      if (!isPdf) {
        final content = 'Título: ${article.title}\nAutores: ${article.authors.join(", ")}\n\nEnlace PDF: ${article.pdfUrl ?? "N/A"}\nEnlace Oficial: ${article.url ?? "N/A"}\n\nResumen:\n${article.abstractText}\n\nBibTeX:\n${article.generateBibtex()}';
        fileBytes = utf8.encode(content);
      }

      final sanitizeTitle = article.title.replaceAll(RegExp(r'[/\\?%*:|"<>]'), '_');
      final fileName = isPdf ? '$sanitizeTitle.pdf' : '$sanitizeTitle.txt';
      final mimeType = isPdf ? 'application/pdf' : 'text/plain';

      final driveFile = drive.File()
        ..name = fileName
        ..mimeType = mimeType;

      final media = drive.Media(
        Stream.value(fileBytes),
        fileBytes.length,
      );

      await driveApi.files.create(driveFile, uploadMedia: media);
      return true;
    } catch (e) {
      debugPrint('Error en GoogleDriveService: $e');
      rethrow;
    }
  }
}
