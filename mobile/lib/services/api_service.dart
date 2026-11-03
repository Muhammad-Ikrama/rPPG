import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/vital_sign.dart';

class ApiService {
  String baseUrl = 'http://10.0.2.2:8000'; // Default Android emulator host loopback
  String? _token;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString('server_url') ?? 'http://10.0.2.2:8000';
    _token = prefs.getString('auth_token');
  }

  void setBaseUrl(String url) async {
    baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', url);
  }

  Map<String, String> _headers([bool isJson = true]) {
    final headers = <String, String>{};
    if (isJson) headers['Content-Type'] = 'application/json';
    if (_token != null) headers['Authorization'] = 'Bearer $_token';
    return headers;
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/login'),
      headers: _headers(),
      body: jsonEncode({'email': email, 'password': password}),
    );
    if (response.statusCode != 200) {
      final err = jsonDecode(response.body);
      throw Exception(err['detail'] ?? 'Login failed');
    }
    final data = jsonDecode(response.body);
    _token = data['access_token'];
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('auth_token', _token!);
    return data;
  }

  Future<Map<String, dynamic>> register(
      String email, String password, String fullName, bool consent) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/register'),
      headers: _headers(),
      body: jsonEncode({
        'email': email,
        'password': password,
        'full_name': fullName,
        'consent_accepted': consent,
      }),
    );
    if (response.statusCode != 200) {
      final err = jsonDecode(response.body);
      throw Exception(err['detail'] ?? 'Registration failed');
    }
    final data = jsonDecode(response.body);
    _token = data['access_token'];
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('auth_token', _token!);
    return data;
  }

  Future<String> createSession() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/measurements/session'),
      headers: _headers(),
      body: jsonEncode({
        'camera_type': 'mobile_front_camera',
        'resolution': '1280x720',
        'fps': 30.0,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to initialize measurement session');
    }
    final data = jsonDecode(response.body);
    return data['session_id'];
  }

  Future<void> uploadVideo(String sessionId, String videoFilePath) async {
    final uri = Uri.parse('$baseUrl/api/v1/measurements/upload/$sessionId');
    final request = http.MultipartRequest('POST', uri);
    if (_token != null) request.headers['Authorization'] = 'Bearer $_token';

    request.files.add(await http.MultipartFile.fromPath('video', videoFilePath));
    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200) {
      throw Exception('Video upload failed with status ${response.statusCode}');
    }
  }

  Future<DashboardData> runInstantDemo() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/measurements/synthetic-demo?target_hr=74.0&target_rr=16.0'),
      headers: _headers(),
    );
    if (response.statusCode != 200) {
      throw Exception('Demo execution failed');
    }
    return DashboardData.fromJson(jsonDecode(response.body));
  }

  Future<Map<String, dynamic>> checkStatus(String sessionId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/measurements/status/$sessionId'),
      headers: _headers(),
    );
    if (response.statusCode != 200) throw Exception('Status check failed');
    return jsonDecode(response.body);
  }

  Future<DashboardData> getResults(String sessionId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/measurements/results/$sessionId'),
      headers: _headers(),
    );
    if (response.statusCode != 200) throw Exception('Failed to load results');
    return DashboardData.fromJson(jsonDecode(response.body));
  }

  Future<List<SessionListItem>> getHistory() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/measurements/history'),
      headers: _headers(),
    );
    if (response.statusCode != 200) throw Exception('Failed to load history');
    final data = jsonDecode(response.body);
    final list = data['sessions'] as List<dynamic>? ?? [];
    return list.map((e) => SessionListItem.fromJson(e)).toList();
  }

  Future<Map<String, dynamic>> compareAllAlgorithms({
    required List<List<double>> rgbSignals,
    double fps = 30.0,
    double? referenceHrBpm,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/models/compare-all'),
      headers: _headers(),
      body: jsonEncode({
        'rgb_signals': rgbSignals,
        'fps': fps,
        'reference_hr_bpm': referenceHrBpm,
      }),
    );
    if (response.statusCode != 200) throw Exception('Multi-algorithm comparison failed');
    return jsonDecode(response.body);
  }

  Future<List<dynamic>> getExperiments() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/models/experiments'),
      headers: _headers(),
    );
    if (response.statusCode != 200) throw Exception('Failed to load DL experiments');
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> triggerTrainingExperiment({
    String experimentName = 'PhysNet_Mobile_Run',
    int numEpochs = 2,
    int numSubjects = 8,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/models/train'),
      headers: _headers(),
      body: jsonEncode({
        'experiment_name': experimentName,
        'num_epochs': numEpochs,
        'num_subjects': numSubjects,
        'batch_size': 2,
        'learning_rate': 0.001,
        'random_seed': 42,
      }),
    );
    if (response.statusCode != 200) throw Exception('Training trigger failed');
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> getCohortRecordings() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/cohort/recordings'),
      headers: _headers(),
    );
    if (response.statusCode != 200) throw Exception('Failed to load cohort recordings');
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> runCohortValidation() async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/cohort/validate-all'),
      headers: _headers(),
    );
    if (response.statusCode != 200) throw Exception('Cohort validation failed');
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> getDatasetCompatibility() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/datasets/compatibility'),
      headers: _headers(),
    );
    if (response.statusCode != 200) throw Exception('Failed to load dataset matrix');
    return jsonDecode(response.body);
  }
}
