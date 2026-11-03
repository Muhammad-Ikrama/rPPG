import 'dart:async';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:provider/provider.dart';
import '../../providers/measurement_provider.dart';
import '../theme.dart';
import '../widgets/face_overlay_painter.dart';
import 'processing_screen.dart';

class MeasurementScreen extends StatefulWidget {
  const MeasurementScreen({Key? key}) : super(key: key);

  @override
  State<MeasurementScreen> createState() => _MeasurementScreenState();
}

class _MeasurementScreenState extends State<MeasurementScreen> {
  CameraController? _controller;
  bool _isCameraInitialized = false;
  bool _isRecording = false;
  int _secondsRemaining = 15;
  Timer? _countdownTimer;
  String _guidance = 'Align face inside oval guide.';

  @override
  void initState() {
    super.initState();
    _initializeFrontCamera();
  }

  Future<void> _initializeFrontCamera() async {
    try {
      final cameras = await availableCameras();
      final frontCamera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      _controller = CameraController(
        frontCamera,
        ResolutionPreset.medium,
        enableAudio: false,
      );

      await _controller!.initialize();
      if (mounted) {
        setState(() => _isCameraInitialized = true);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _guidance = 'Camera initialization failed: $e');
      }
    }
  }

  Future<void> _startRecording() async {
    if (_controller == null || !_controller!.value.isInitialized || _isRecording) return;

    try {
      await _controller!.startVideoRecording();
      setState(() {
        _isRecording = true;
        _secondsRemaining = 15;
        _guidance = 'Recording in progress... Remain completely still.';
      });

      _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (_secondsRemaining > 1) {
          setState(() => _secondsRemaining--);
        } else {
          _stopRecording();
        }
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not start recording: $e')),
      );
    }
  }

  Future<void> _stopRecording() async {
    if (_countdownTimer != null) {
      _countdownTimer!.cancel();
      _countdownTimer = null;
    }

    if (_controller != null && _controller!.value.isRecordingVideo) {
      final file = await _controller!.stopVideoRecording();
      setState(() => _isRecording = false);

      if (mounted) {
        // Dispatch to background processing and open processing screen
        final provider = context.read<MeasurementProvider>();
        provider.processRecordedVideo(file.path);

        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const ProcessingScreen()),
        );
      }
    }
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Live Optical Capture')),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (_isCameraInitialized && _controller != null)
                    CameraPreview(_controller!)
                  else
                    const Center(
                      child: CircularProgressIndicator(color: BiomedicalTheme.accentTeal),
                    ),
                  // Face Alignment Overlay
                  CustomPaint(
                    painter: FaceOverlayPainter(isAligned: _isRecording),
                  ),
                  // Top Guidance Banner
                  Positioned(
                    top: 20,
                    left: 20,
                    right: 20,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.7),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: BiomedicalTheme.accentTeal.withOpacity(0.5)),
                      ),
                      child: Text(
                        _guidance,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: BiomedicalTheme.accentTeal,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                  // Countdown overlay during recording
                  if (_isRecording)
                    Positioned(
                      bottom: 40,
                      left: 0,
                      right: 0,
                      child: Center(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                          decoration: BoxDecoration(
                            color: BiomedicalTheme.accentRose,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            'Recording: $_secondsRemaining s',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                              fontSize: 16,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            // Bottom control bar
            Container(
              padding: const EdgeInsets.all(20.0),
              color: BiomedicalTheme.cardNavy,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  ElevatedButton(
                    onPressed: _isCameraInitialized && !_isRecording ? _startRecording : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: BiomedicalTheme.accentTeal,
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                    ),
                    child: const Text('Start 15s Recording'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
