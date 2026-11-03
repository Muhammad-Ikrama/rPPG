import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
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
  bool _consent = true;

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
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Checkbox(
                      value: _consent,
                      activeColor: BiomedicalTheme.accentTeal,
                      onChanged: (v) => setState(() => _consent = v ?? false),
                    ),
                    const Expanded(
                      child: Text(
                        'I consent to facial video recording under biomedical research protocols and pseudonymized ID storage.',
                        style: TextStyle(fontSize: 11, color: Colors.white70),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 24),
              if (provider.errorMessage != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16.0),
                  child: Text(
                    provider.errorMessage!,
                    style: const TextStyle(color: BiomedicalTheme.accentRose, fontSize: 13),
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
                          if (_isRegister) {
                            if (!_consent) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Research consent required')),
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
                      : Text(_isRegister ? 'Register' : 'Sign In'),
                ),
              ),
              const SizedBox(height: 16),
              Center(
                child: TextButton(
                  onPressed: () {
                    setState(() => _isRegister = !_isRegister);
                  },
                  child: Text(
                    _isRegister
                        ? 'Already have an account? Sign in'
                        : 'New participant? Register with consent',
                    style: const TextStyle(color: BiomedicalTheme.accentTeal),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
