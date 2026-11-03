import 'package:flutter/material.dart';
import '../theme.dart';
import 'login_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 36.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 20),
                  Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: BiomedicalTheme.accentTeal.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: BiomedicalTheme.accentTeal, width: 2),
                    ),
                    child: const Icon(Icons.favorite, color: BiomedicalTheme.accentTeal, size: 30),
                  ),
                  const SizedBox(height: 28),
                  const Text(
                    'rPPG Vital Signs\nMonitoring',
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Non-contact physiological estimation using Plane-Orthogonal-to-Skin (POS) optical computer vision.',
                    style: TextStyle(
                      fontSize: 15,
                      color: BiomedicalTheme.textMuted,
                      height: 1.4,
                    ),
                  ),
                  const SizedBox(height: 24),
                  _buildFeatureBullet(Icons.check_circle_outline, 'Heart Rate & Respiratory Rate estimation'),
                  _buildFeatureBullet(Icons.check_circle_outline, 'Experimental SpO2 & Blood Pressure analysis'),
                  _buildFeatureBullet(Icons.lock_outline, 'Pseudonymized biometric privacy & ISO 81060-2 compliance'),
                ],
              ),
              Column(
                children: [
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const LoginScreen()),
                        );
                      },
                      child: const Text('Access Research System'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Developed for Biomedical Engineering Research\nNot a certified diagnostic medical device',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11, color: BiomedicalTheme.slateGrey),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeatureBullet(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        children: [
          Icon(icon, color: BiomedicalTheme.accentTeal, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text,
                style: const TextStyle(fontSize: 13, color: Colors.white70)),
          ),
        ],
      ),
    );
  }
}
