import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/api_config.dart';
import '../../providers/measurement_provider.dart';
import '../theme.dart';
import 'dashboard_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController(text: 'demo_researcher@fyp.edu');
  final _passwordController = TextEditingController(text: 'ResearchPassword123!');
  final _nameController = TextEditingController();
  bool _isRegister = false;
  bool _consent = false; // Strictly unchecked by default for biomedical research protocol

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MeasurementProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text(_isRegister ? 'Research Participant Registration' : 'Sign In'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _isRegister ? 'Join Clinical Research Study' : 'Welcome Back',
                style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              const Text(
                'Enter credentials to access rPPG cloud session processing.',
                style: TextStyle(fontSize: 13, color: BiomedicalTheme.textMuted),
              ),
              const SizedBox(height: 24),
              if (_isRegister) ...[
                TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(
                    labelText: 'Full Name',
                    border: OutlineInputBorder(),
                    filled: true,
                    fillColor: BiomedicalTheme.cardNavy,
                  ),
                ),
                const SizedBox(height: 16),
              ],
              TextField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email Address',
                  border: OutlineInputBorder(),
                  filled: true,
                  fillColor: BiomedicalTheme.cardNavy,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordController,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                  filled: true,
                  fillColor: BiomedicalTheme.cardNavy,
                ),
              ),
              if (_isRegister) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: BiomedicalTheme.cardNavy,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: _consent ? BiomedicalTheme.accentTeal : Colors.white24,
                    ),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Checkbox(
                        value: _consent,
                        activeColor: BiomedicalTheme.accentTeal,
                        onChanged: (v) => setState(() => _consent = v ?? false),
                      ),
                      const Expanded(
                        child: Text(
                          'I consent to facial video recording under biomedical research protocols and pseudonymized ID storage for vital sign estimation.',
                          style: TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 24),
              if (provider.errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16.0),
                  decoration: BoxDecoration(
                    color: BiomedicalTheme.accentRose.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: BiomedicalTheme.accentRose.withOpacity(0.4)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.error_outline, color: BiomedicalTheme.accentRose, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          provider.errorMessage!,
                          style: const TextStyle(color: Colors.white, fontSize: 12),
                        ),
                      ),
                    ],
                  ),
                ),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: provider.isLoading
                      ? null
                      : () async {
                          final email = _emailController.text.trim();
                          final password = _passwordController.text;

                          if (email.isEmpty || password.isEmpty) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Please enter both email and password')),
                            );
                            return;
                          }

                          if (_isRegister) {
                            if (!_consent) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Explicit biometric research consent is required to register'),
                                  backgroundColor: BiomedicalTheme.accentRose,
                                ),
                              );
                              return;
                            }
                            await provider.register(
                              email,
                              password,
                              _nameController.text.trim(),
                              _consent,
                            );
                          } else {
                            await provider.login(email, password);
                          }

                          if (provider.errorMessage == null && mounted) {
                            Navigator.pushReplacement(
                              context,
                              MaterialPageRoute(builder: (_) => const DashboardScreen()),
                            );
                          }
                        },
                  child: provider.isLoading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(color: BiomedicalTheme.primaryNavy),
                        )
                      : Text(_isRegister ? 'Register Participant' : 'Sign In'),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () async {
                    await provider.runDemo();
                    if (mounted) {
                      Navigator.pushReplacement(
                        context,
                        MaterialPageRoute(builder: (_) => const DashboardScreen()),
                      );
                    }
                  },
                  icon: const Icon(Icons.bolt, color: BiomedicalTheme.accentTeal),
                  label: const Text('Instant Demo Mode (Offline / Direct)'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: BiomedicalTheme.accentTeal,
                    side: const BorderSide(color: BiomedicalTheme.accentTeal),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Center(
                child: TextButton(
                  onPressed: () {
                    provider.clearError(); // Clear any previous error when switching screens
                    setState(() {
                      _isRegister = !_isRegister;
                      _consent = false; // Reset consent on switch
                    });
                  },
                  child: Text(
                    _isRegister
                        ? 'Already have an account? Sign in'
                        : 'New participant? Register with consent',
                    style: const TextStyle(color: BiomedicalTheme.accentTeal),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Center(
                child: TextButton.icon(
                  onPressed: () => _showServerConfigDialog(context, provider),
                  icon: const Icon(Icons.settings_ethernet, size: 16, color: BiomedicalTheme.slateGrey),
                  label: Text(
                    'Server: ${provider.apiService.baseUrl}',
                    style: const TextStyle(fontSize: 12, color: BiomedicalTheme.slateGrey),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showServerConfigDialog(BuildContext context, MeasurementProvider provider) {
    final controller = TextEditingController(text: provider.apiService.baseUrl);
    String probeStatus = '';
    bool isProbing = false;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: BiomedicalTheme.cardNavy,
          title: const Text('Configure Backend Server URL', style: TextStyle(fontSize: 16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'If testing on a physical phone via Wi-Fi, select PC Wi-Fi:',
                style: TextStyle(fontSize: 12, color: BiomedicalTheme.textMuted),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                decoration: const InputDecoration(
                  labelText: 'Server Base URL',
                  hintText: 'http://192.168.100.103:8000',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                children: [
                  ActionChip(
                    label: const Text('PC Wi-Fi (192.168.100.103)', style: TextStyle(fontSize: 10)),
                    onPressed: () => controller.text = ApiConfig.lanUrl,
                  ),
                  ActionChip(
                    label: const Text('Emulator (10.0.2.2)', style: TextStyle(fontSize: 10)),
                    onPressed: () => controller.text = ApiConfig.emulatorUrl,
                  ),
                  ActionChip(
                    label: const Text('Localhost (127.0.0.1)', style: TextStyle(fontSize: 10)),
                    onPressed: () => controller.text = ApiConfig.localhostUrl,
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white12,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                    ),
                    onPressed: isProbing
                        ? null
                        : () async {
                            setDialogState(() {
                              isProbing = true;
                              probeStatus = 'Testing connection...';
                            });
                            final ok = await ApiConfig.checkHealth(controller.text.trim());
                            setDialogState(() {
                              isProbing = false;
                              probeStatus = ok
                                  ? '✓ Server reachable & healthy'
                                  : '✗ Server unreachable';
                            });
                          },
                    icon: const Icon(Icons.wifi_tethering, size: 14),
                    label: const Text('Test Connection', style: TextStyle(fontSize: 11)),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      probeStatus,
                      style: TextStyle(
                        fontSize: 11,
                        color: probeStatus.startsWith('✓')
                            ? BiomedicalTheme.accentTeal
                            : probeStatus.startsWith('✗')
                                ? BiomedicalTheme.accentRose
                                : Colors.white70,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                final url = controller.text.trim();
                if (url.isNotEmpty) {
                  provider.apiService.setBaseUrl(url);
                  provider.clearError();
                }
                Navigator.pop(ctx);
                setState(() {});
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }
}
