import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/search_provider.dart';
import '../widgets/article_card.dart';

class FavoritesView extends StatelessWidget {
  const FavoritesView({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SearchProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Favoritos Guardados ⭐'),
      ),
      body: provider.favorites.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.bookmark_border_rounded, size: 64, color: Colors.grey),
                  SizedBox(height: 16),
                  Text(
                    'No tienes artículos guardados en favoritos.',
                    style: TextStyle(color: Colors.grey, fontSize: 16),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Toca el ícono del marcador en cualquier artículo para guardarlo.',
                    style: TextStyle(color: Colors.grey, fontSize: 12),
                  ),
                ],
              ),
            )
          : ListView.builder(
              itemCount: provider.favorites.length,
              itemBuilder: (context, index) {
                return ArticleCard(article: provider.favorites[index]);
              },
            ),
    );
  }
}
