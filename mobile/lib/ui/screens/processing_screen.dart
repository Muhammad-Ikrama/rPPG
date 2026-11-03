import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/measurement_provider.dart';
import '../theme.dart';
import 'dashboard_screen.dart';

class ProcessingScreen extends StatelessWidget {
  const ProcessingScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MeasurementProvider>();

    // If processing finished, pop back to dashboard
    if (!provider.isLoading && provider.currentData != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(builder: (_) => const DashboardScreen()),
          (route) => false,
        );
      });
    }

    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const SizedBox(
                width: 64,
                height: 64,
                child: CircularProgressIndicator(
                  strokeWidth: 4,
                  valueColor: AlwaysStoppedAnimation<Color>(BiomedicalTheme.accentTeal),
                ),
              ),
              const SizedBox(height: 32),
              const Text(
                'Cloud Signal Analysis',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              Text(
                provider.processingStage.isNotEmpty
                    ? provider.processingStage
                    : 'Extracting optical rPPG pulse via Plane-Orthogonal-to-Skin...',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: BiomedicalTheme.textMuted),
              ),
              if (provider.errorMessage != null) ...[
                const SizedBox(height: 24),
                Text(
                  'Error: ${provider.errorMessage}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: BiomedicalTheme.accentRose, fontSize: 13),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () {
                    Navigator.pushAndRemoveUntil(
                      context,
                      MaterialPageRoute(builder: (_) => const DashboardScreen()),
                      (route) => false,
                    );
                  },
                  child: const Text('Return to Dashboard'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
