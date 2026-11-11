import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiConfig {
  static const String lanUrl = 'http://192.168.100.103:8000';
  static const String emulatorUrl = 'http://10.0.2.2:8000';
  static const String localhostUrl = 'http://127.0.0.1:8000';
  static const String defaultUrl = lanUrl; // Physical device LAN IP as primary default

  static const List<String> presetUrls = [
    lanUrl,
    emulatorUrl,
    localhostUrl,
  ];

  /// Probe a server's /health endpoint with a 1.5-second timeout.
  static Future<bool> checkHealth(String baseUrl) async {
    try {
      final sanitized = baseUrl.trim().replaceAll(RegExp(r'/+$'), '');
      final uri = Uri.parse('$sanitized/health');
      final res = await http.get(uri).timeout(const Duration(milliseconds: 1500));
      if (res.statusCode == 200) {
        final body = jsonDecode(res.body);
        return body['status'] == 'HEALTHY';
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  /// Probes candidates in priority order and returns the first healthy URL.
  static Future<String> discoverHealthyServer({String? preferredUrl}) async {
    if (preferredUrl != null && preferredUrl.isNotEmpty) {
      if (await checkHealth(preferredUrl)) {
        return preferredUrl;
      }
    }

    // Try LAN Wi-Fi first (physical phone), then emulator, then localhost
    for (final candidate in presetUrls) {
      if (await checkHealth(candidate)) {
        return candidate;
      }
    }

    // Fallback to LAN default if offline/unreachable
    return preferredUrl ?? defaultUrl;
  }
}

