import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/measurement_provider.dart';
import '../theme.dart';
import 'welcome_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    final provider = context.read<MeasurementProvider>();
    _urlController = TextEditingController(text: provider.apiService.baseUrl);
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MeasurementProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Settings & Ethics')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('CLOUD BACKEND CONFIGURATION',
              style: TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w700, color: BiomedicalTheme.textMuted)),
          const SizedBox(height: 10),
          TextField(
            controller: _urlController,
            decoration: const InputDecoration(
              labelText: 'Backend Server URL',
              border: OutlineInputBorder(),
              filled: true,
              fillColor: BiomedicalTheme.cardNavy,
              helperText: 'e.g. http://10.0.2.2:8000 for Android emulator or public HTTPS URL',
            ),
          ),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: () {
              provider.apiService.setBaseUrl(_urlController.text.trim());
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Server URL updated')),
              );
            },
            child: const Text('Save Server URL'),
          ),
          const SizedBox(height: 32),
          const Text('BIOMEDICAL RESEARCH METHODOLOGY',
              style: TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w700, color: BiomedicalTheme.textMuted)),
          const SizedBox(height: 10),
          _buildInfoTile('Algorithm Engine', 'POS (Plane-Orthogonal-to-Skin, Wang et al. 2017)'),
          _buildInfoTile('Blood Pressure Model', 'Experimental Pulse Morphology (ISO 81060-2 Disclosure)'),
          _buildInfoTile('SpO2 Model', 'Optical RoR Research Proxy (Uncalibrated Bayer limitations)'),
          _buildInfoTile('Data Retention', '7-Day Automatic Cloud Deletion with SHA-256 Checksums'),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              style: OutlinedButton.styleFrom(
                foregroundColor: BiomedicalTheme.accentRose,
                side: const BorderSide(color: BiomedicalTheme.accentRose),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              onPressed: () {
                Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder: (_) => const WelcomeScreen()),
                  (route) => false,
                );
              },
              child: const Text('Sign Out & Purge Local Cache'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoTile(String title, String desc) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: BiomedicalTheme.cardNavy,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
          const SizedBox(height: 2),
          Text(desc, style: const TextStyle(fontSize: 11, color: BiomedicalTheme.textMuted)),
        ],
      ),
    );
  }
}
