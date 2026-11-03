import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/measurement_provider.dart';
import 'ui/theme.dart';
import 'ui/screens/welcome_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final measurementProvider = MeasurementProvider();
  await measurementProvider.initialize();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: measurementProvider),
      ],
      child: const RPPGVitalSignsApp(),
    ),
  );
}

class RPPGVitalSignsApp extends StatelessWidget {
  const RPPGVitalSignsApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'rPPG Vital Signs Monitor',
      debugShowCheckedModeBanner: false,
      theme: BiomedicalTheme.darkTheme,
      home: const WelcomeScreen(),
    );
  }
}
