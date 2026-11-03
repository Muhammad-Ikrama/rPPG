import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/measurement_provider.dart';
import '../theme.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MeasurementProvider>();
    final history = provider.history;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Measurement History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => provider.fetchHistory(),
          ),
        ],
      ),
      body: history.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  Icon(Icons.history, size: 48, color: BiomedicalTheme.slateGrey),
                  SizedBox(height: 12),
                  Text('No measurements recorded yet',
                      style: TextStyle(color: BiomedicalTheme.textMuted)),
                ],
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: history.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final item = history[index];
                return Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: BiomedicalTheme.cardNavy,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.white.withOpacity(0.06)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: BiomedicalTheme.accentTeal.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.monitor_heart,
                            color: BiomedicalTheme.accentTeal, size: 22),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Session: ${item.id.substring(0, 8)}',
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              item.createdAt.isNotEmpty
                                  ? item.createdAt.substring(0, 16).replaceAll('T', ' ')
                                  : '',
                              style: const TextStyle(
                                  fontSize: 11, color: BiomedicalTheme.textMuted),
                            ),
                            const SizedBox(height: 6),
                            Wrap(
                              spacing: 8,
                              children: [
                                if (item.hrBpm != null)
                                  Text('HR: ${item.hrBpm!.toStringAsFixed(1)} BPM',
                                      style: const TextStyle(fontSize: 11, color: Colors.white70)),
                                if (item.rrBrpm != null)
                                  Text('RR: ${item.rrBrpm!.toStringAsFixed(1)} BrPM',
                                      style: const TextStyle(fontSize: 11, color: Colors.white70)),
                                if (item.spo2Percent != null)
                                  Text('SpO2: ${item.spo2Percent!.toStringAsFixed(1)}%',
                                      style: const TextStyle(fontSize: 11, color: Colors.white70)),
                              ],
                            ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: BiomedicalTheme.accentGreen.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          item.sqiStatus,
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            color: BiomedicalTheme.accentGreen,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
