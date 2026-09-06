import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/search_provider.dart';
import '../widgets/article_card.dart';

class SearchView extends StatefulWidget {
  const SearchView({super.key});

  @override
  State<SearchView> createState() => _SearchViewState();
}

class _SearchViewState extends State<SearchView> {
  final TextEditingController _customQueryCtrl = TextEditingController();

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SearchProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('SearchForLens 🔭'),
      ),
      body: Column(
        children: [
          // Filter Panel (Preset Chips & Inputs)
          Container(
            padding: const EdgeInsets.all(16),
            color: const Color(0xFF1E293B),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Preset Chips
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      ChoiceChip(
                        label: const Text('🌌 Lentes Fuertes'),
                        selected: provider.presetType == 'strong_lensing',
                        onSelected: (val) {
                          if (val) provider.updateFilters(presetType: 'strong_lensing');
                        },
                      ),
                      const SizedBox(width: 8),
                      ChoiceChip(
                        label: const Text('🧠 IA en Lentes'),
                        selected: provider.presetType == 'ai_lensing',
                        onSelected: (val) {
                          if (val) provider.updateFilters(presetType: 'ai_lensing');
                        },
                      ),
                      const SizedBox(width: 8),
                      ChoiceChip(
                        label: const Text('🔍 Personalizada'),
                        selected: provider.presetType == 'custom',
                        onSelected: (val) {
                          if (val) provider.updateFilters(presetType: 'custom');
                        },
                      ),
                    ],
                  ),
                ),

                // Custom Query Field (if custom selected)
                if (provider.presetType == 'custom') ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: _customQueryCtrl,
                    decoration: const InputDecoration(
                      hintText: 'Términos de búsqueda...',
                      prefixIcon: Icon(Icons.search),
                      filled: true,
                      fillColor: Color(0xFF0F172A),
                      border: OutlineInputBorder(borderRadius: BorderRadius.all(Radius.circular(12))),
                    ),
                    onChanged: (val) => provider.updateFilters(customQuery: val),
                  ),
                ],

                const SizedBox(height: 12),

                // Search Button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF38BDF8),
                      foregroundColor: const Color(0xFF0F172A),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    icon: const Icon(Icons.search_rounded),
                    label: const Text(
                      'Buscar Artículos',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                    ),
                    onPressed: provider.isLoading ? null : () => provider.performSearch(),
                  ),
                ),
              ],
            ),
          ),

          // Loading & Status
          if (provider.isLoading) ...[
            const LinearProgressIndicator(color: Color(0xFF38BDF8)),
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: Text(
                provider.statusMessage,
                style: const TextStyle(color: Color(0xFF38BDF8), fontStyle: FontStyle.italic),
              ),
            ),
          ],

          // Errors banner
          if (provider.errors.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(8),
              color: Colors.amber.withOpacity(0.15),
              child: Text(
                provider.errors.join('\n'),
                style: const TextStyle(color: Colors.amber, fontSize: 12),
              ),
            ),

          // Results Header Summary
          if (provider.articles.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  Text(
                    '${provider.articles.length} artículos encontrados',
                    style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const Spacer(),
                  Text(
                    provider.sourceSummary,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF38BDF8)),
                  ),
                ],
              ),
            ),

          // Results List
          Expanded(
            child: provider.articles.isEmpty && !provider.isLoading
                ? const Center(
                    child: Text(
                      'Presiona "Buscar Artículos" para consultar arXiv, NASA ADS e INSPIRE-HEP.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.grey),
                    ),
                  )
                : ListView.builder(
                    itemCount: provider.articles.length,
                    itemBuilder: (context, index) {
                      return ArticleCard(article: provider.articles[index]);
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
