import 'package:flutter/material.dart';
import '../theme.dart';

class WaveformPainter extends CustomPainter {
  final List<double> waveform;

  WaveformPainter({required this.waveform});

  @override
  void paint(Canvas canvas, Size size) {
    if (waveform.isEmpty) return;

    final w = size.width;
    final h = size.height;

    // Draw baseline
    final baselinePaint = Paint()
      ..color = Colors.white.withOpacity(0.08)
      ..strokeWidth = 1.0;
    canvas.drawLine(Offset(0, h / 2), Offset(w, h / 2), baselinePaint);

    double minVal = waveform.reduce((a, b) => a < b ? a : b);
    double maxVal = waveform.reduce((a, b) => a > b ? a : b);
    double range = maxVal - minVal;
    if (range < 1e-4) range = 1.0;

    final stepX = w / (waveform.length - 1);
    final path = Path();

    double getY(double val) {
      final norm = (val - minVal) / range;
      return h - (norm * (h - 20) + 10);
    }

    path.moveTo(0, getY(waveform[0]));
    for (int i = 1; i < waveform.length; i++) {
      path.lineTo(i * stepX, getY(waveform[i]));
    }

    // Gradient fill under waveform
    final fillPath = Path.from(path)
      ..lineTo(w, h)
      ..lineTo(0, h)
      ..close();

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          BiomedicalTheme.accentTeal.withOpacity(0.3),
          BiomedicalTheme.accentTeal.withOpacity(0.0),
        ],
      ).createShader(Rect.fromLTWH(0, 0, w, h))
      ..style = PaintingStyle.fill;

    canvas.drawPath(fillPath, fillPaint);

    final linePaint = Paint()
      ..color = BiomedicalTheme.accentTeal
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    canvas.drawPath(path, linePaint);
  }

  @override
  bool shouldRepaint(covariant WaveformPainter oldDelegate) {
    return oldDelegate.waveform != waveform;
  }
}
