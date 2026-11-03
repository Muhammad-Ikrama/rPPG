import 'package:flutter/material.dart';
import '../models/vital_sign.dart';
import '../theme.dart';

class VitalCard extends StatelessWidget {
  final String title;
  final VitalSignMetric metric;
  final IconData icon;
  final Color accentColor;
  final String? subtitle;

  const VitalCard({
    Key? key,
    required this.title,
    required this.metric,
    required this.icon,
    required this.accentColor,
    this.subtitle,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final hasVal = metric.value != null;
    final valStr = hasVal ? metric.value!.toStringAsFixed(1) : '--';

    return Container(
      decoration: BoxDecoration(
        color: BiomedicalTheme.cardNavy,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.08)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Top accent strip
          Container(
            height: 3,
            decoration: BoxDecoration(
              color: accentColor,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color: accentColor.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Icon(icon, color: accentColor, size: 20),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          title,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: BiomedicalTheme.textMuted,
                          ),
                        ),
                      ],
                    ),
                    _buildStatusPill(metric.status),
                  ],
                ),
                const SizedBox(height: 14),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      valStr,
                      style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      metric.unit,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: BiomedicalTheme.textMuted,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                // Confidence bar
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Confidence',
                        style: TextStyle(fontSize: 11, color: BiomedicalTheme.textMuted)),
                    Text(
                      '${(metric.confidence * 100).toInt()}%',
                      style: const TextStyle(
                          fontSize: 11, fontWeight: FontWeight.w600, color: Colors.white),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: metric.confidence,
                    backgroundColor: Colors.white.withOpacity(0.06),
                    valueColor: AlwaysStoppedAnimation<Color>(accentColor),
                    minHeight: 4,
                  ),
                ),
                if (metric.isExperimental) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: BiomedicalTheme.accentAmber.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                          color: BiomedicalTheme.accentAmber.withOpacity(0.2)),
                    ),
                    child: Text(
                      metric.disclaimer ?? 'Experimental Research Objective (ISO 81060-2)',
                      style: const TextStyle(
                        fontSize: 10,
                        color: BiomedicalTheme.accentAmber,
                        height: 1.3,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusPill(String status) {
    Color bg = Colors.white.withOpacity(0.1);
    Color fg = Colors.white70;

    final lower = status.toLowerCase();
    if (lower == 'excellent' || lower == 'good') {
      bg = BiomedicalTheme.accentGreen.withOpacity(0.15);
      fg = BiomedicalTheme.accentGreen;
    } else if (lower.contains('exp') || lower == 'fair') {
      bg = BiomedicalTheme.accentAmber.withOpacity(0.15);
      fg = BiomedicalTheme.accentAmber;
    } else if (lower == 'unreliable' || lower == 'unavailable') {
      bg = BiomedicalTheme.accentRose.withOpacity(0.15);
      fg = BiomedicalTheme.accentRose;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status.toUpperCase(),
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w700,
          color: fg,
        ),
      ),
    );
  }
}
