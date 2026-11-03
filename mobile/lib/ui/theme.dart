import 'package:flutter/material.dart';

class BiomedicalTheme {
  static const Color primaryNavy = Color(0xFF0B192C);
  static const Color secondaryNavy = Color(0xFF1E3E62);
  static const Color cardNavy = Color(0xFF132238);
  static const Color accentTeal = Color(0xFF00ADB5);
  static const Color accentGreen = Color(0xFF10B981);
  static const Color accentAmber = Color(0xFFF59E0B);
  static const Color accentRose = Color(0xFFF43F5E);
  static const Color accentBlue = Color(0xFF3B82F6);
  static const Color slateGrey = Color(0xFF64748B);
  static const Color textMuted = Color(0xFF94A3B8);
  static const Color backgroundDark = primaryNavy;

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      primaryColor: primaryNavy,
      scaffoldBackgroundColor: primaryNavy,
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: primaryNavy,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Colors.white,
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
      ),
      cardTheme: CardTheme(
        color: cardNavy,
        elevation: 4,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0x2064748B), width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: accentTeal,
          foregroundColor: primaryNavy,
          elevation: 2,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      colorScheme: const ColorScheme.dark(
        primary: accentTeal,
        secondary: accentBlue,
        surface: cardNavy,
        background: primaryNavy,
      ),
    );
  }
}
