import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/measurement_provider.dart';
import '../theme.dart';
import '../widgets/vital_card.dart';
import '../widgets/waveform_painter.dart';
import 'measurement_screen.dart';
import 'history_screen.dart';
import 'settings_screen.dart';
import 'research_screen.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MeasurementProvider>();
    final data = provider.currentData;

    return Scaffold(
      appBar: AppBar(
        title: const Text('rPPG Vital Signs Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.biotech_outlined),
            tooltip: 'Biomedical Research Lab',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ResearchScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const HistoryScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SettingsScreen()),
              );
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top action bar
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Subject Physiological Status',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    Text(
                      data != null
                          ? 'Session: ${data.sessionId.substring(0, 8)}'
                          : 'No active session. Run measurement or demo.',
                      style: const TextStyle(fontSize: 12, color: BiomedicalTheme.textMuted),
                    ),
                  ],
                ),
                ElevatedButton.icon(
                  onPressed: provider.isLoading ? null : () => provider.runDemo(),
                  icon: const Icon(Icons.play_arrow, size: 16),
                  label: const Text('Run Demo', style: TextStyle(fontSize: 12)),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),

            // 4 Dedicated Measurement Cards: HR, RR, SpO2, BP
            if (data != null) ...[
              VitalCard(
                title: 'Heart Rate (HR)',
                metric: data.heartRate,
                icon: Icons.favorite,
                accentColor: BiomedicalTheme.accentTeal,
              ),
              const SizedBox(height: 12),
              VitalCard(
                title: 'Respiratory Rate (RR)',
                metric: data.respiratoryRate,
                icon: Icons.air,
                accentColor: BiomedicalTheme.accentBlue,
              ),
              const SizedBox(height: 12),
              VitalCard(
                title: 'Oxygen Saturation (SpO2)',
                metric: data.oxygenSaturation,
                icon: Icons.water_drop,
                accentColor: BiomedicalTheme.accentGreen,
              ),
              const SizedBox(height: 12),
              VitalCard(
                title: 'Blood Pressure (SBP/DBP)',
                metric: data.bloodPressureSbp,
                icon: Icons.speed,
                accentColor: BiomedicalTheme.accentAmber,
              ),
              const SizedBox(height: 20),

              // Waveform Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: BiomedicalTheme.cardNavy,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withOpacity(0.08)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: const [
                        Text('Reconstructed rPPG Waveform',
                            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                        Text('POS Filtered',
                            style: TextStyle(fontSize: 11, color: BiomedicalTheme.accentTeal)),
                      ],
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      height: 120,
                      width: double.infinity,
                      child: CustomPaint(
                        painter: WaveformPainter(waveform: data.rppgWaveform),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Signal Quality Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: BiomedicalTheme.cardNavy,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withOpacity(0.08)),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: BiomedicalTheme.accentTeal.withOpacity(0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Text(
                        '${(data.signalQualityScore * 100).toInt()}%',
                        style: const TextStyle(
                          color: BiomedicalTheme.accentTeal,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Quality: ${data.signalQualityStatus}',
                              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                          const SizedBox(height: 2),
                          Text(
                            data.qualityGuidance,
                            style: const TextStyle(fontSize: 11, color: BiomedicalTheme.textMuted),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ] else ...[
              // Empty State
              Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 60.0),
                  child: Column(
                    children: [
                      Icon(Icons.videocam_outlined,
                          size: 64, color: BiomedicalTheme.slateGrey.withOpacity(0.5)),
                      const SizedBox(height: 16),
                      const Text('Ready for Optical Capture',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 6),
                      const Text(
                        'Position your face in front of the camera or run an instant demo.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 13, color: BiomedicalTheme.textMuted),
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton(
                        onPressed: () => provider.runDemo(),
                        child: const Text('Run Instant Demo'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 80), // Padding for floating action button
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: BiomedicalTheme.accentTeal,
        foregroundColor: BiomedicalTheme.primaryNavy,
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const MeasurementScreen()),
          );
        },
        icon: const Icon(Icons.camera_alt),
        label: const Text('Start Camera Measurement', style: TextStyle(fontWeight: FontWeight.w700)),
      ),
    );
  }
}
