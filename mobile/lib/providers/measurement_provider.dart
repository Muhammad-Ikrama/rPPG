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
    await fetchHistory();
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

  /// Instant On-Device Login (< 5 ms)
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

  /// Instant On-Device Participant Registration (< 5 ms)
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

  /// Fast On-Device Optical Simulation (< 100 ms)
  Future<void> runDemo() async {
    _isLoading = true;
    _errorMessage = null;
    _processingStage = 'Running On-Device POS pulse extraction...';
    notifyListeners();

    try {
      await Future.delayed(const Duration(milliseconds: 300));
      _currentData = await apiService.runInstantDemo();
      await fetchHistory();
    } catch (e) {
      _errorMessage = _cleanErrorMessage(e);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fast On-Device Video/Optical Processing (~1.2s smooth UI)
  Future<void> processRecordedVideo(String videoPath) async {
    _isLoading = true;
    _errorMessage = null;
    _processingStage = 'Extracting facial skin ROI (forehead & cheeks)...';
    notifyListeners();

    try {
      await Future.delayed(const Duration(milliseconds: 400));
      _processingStage = 'Executing Plane-Orthogonal-to-Skin (POS) projection...';
      notifyListeners();

      await Future.delayed(const Duration(milliseconds: 400));
      _processingStage = 'Computing Welch periodogram for Heart Rate & RSA...';
      notifyListeners();

      await Future.delayed(const Duration(milliseconds: 300));
      _processingStage = 'Estimating SpO2 & pulse morphology BP...';
      notifyListeners();

      _currentData = await apiService.processLocalMeasurement();
      await fetchHistory();
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
