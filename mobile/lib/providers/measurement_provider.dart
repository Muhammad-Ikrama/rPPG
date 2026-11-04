import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/vital_sign.dart';
import '../services/api_service.dart';

class MeasurementProvider extends ChangeNotifier {
  final ApiService apiService = ApiService();

  DashboardData? _currentData;
  List<SessionListItem> _history = [];
  bool _isLoading = false;
  String _processingStage = '';
  String? _errorMessage;

  DashboardData? get currentData => _currentData;
  List<SessionListItem> get history => _history;
  bool get isLoading => _isLoading;
  String get processingStage => _processingStage;
  String? get errorMessage => _errorMessage;

  Future<void> initialize() async {
    await apiService.init();
  }

  void clearError() {
    if (_errorMessage != null) {
      _errorMessage = null;
      notifyListeners();
    }
  }

  String _cleanErrorMessage(dynamic error) {
    String msg = error.toString();
    if (msg.startsWith('Exception: ')) {
      msg = msg.substring(11);
    }
    return msg;
  }

  Future<void> login(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await apiService.login(email, password);
      await fetchHistory();
    } catch (e) {
      _errorMessage = _cleanErrorMessage(e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> register(String email, String password, String name, bool consent) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      await apiService.register(email, password, name, consent);
      await fetchHistory();
    } catch (e) {
      _errorMessage = _cleanErrorMessage(e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> runDemo() async {
    _isLoading = true;
    _errorMessage = null;
    _processingStage = 'Simulating POS optical pulse extraction...';
    notifyListeners();

    try {
      _currentData = await apiService.runInstantDemo();
      await fetchHistory();
    } catch (e) {
      _errorMessage = _cleanErrorMessage(e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> processRecordedVideo(String videoPath) async {
    _isLoading = true;
    _errorMessage = null;
    _processingStage = 'Uploading secure video to cloud...';
    notifyListeners();

    try {
      final sessionId = await apiService.createSession();
      await apiService.uploadVideo(sessionId, videoPath);

      _processingStage = 'Executing Plane-Orthogonal-to-Skin (POS)...';
      notifyListeners();

      // Poll status
      int elapsed = 0;
      while (elapsed < 60) {
        await Future.delayed(const Duration(seconds: 1));
        elapsed++;
        final status = await apiService.checkStatus(sessionId);
        if (status['status'] == 'COMPLETED') {
          _processingStage = 'Extracting physiological waveforms...';
          notifyListeners();
          _currentData = await apiService.getResults(sessionId);
          await fetchHistory();
          break;
        } else if (status['status'] == 'FAILED') {
          throw Exception(status['error_message'] ?? 'Processing failed');
        }
      }
    } catch (e) {
      _errorMessage = _cleanErrorMessage(e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> fetchHistory() async {
    try {
      _history = await apiService.getHistory();
      notifyListeners();
    } catch (e) {
      // Ignored
    }
  }
}
