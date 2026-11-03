import 'package:flutter/material.dart';
import '../theme.dart';

class FaceOverlayPainter extends CustomPainter {
  final bool isAligned;

  FaceOverlayPainter({this.isAligned = false});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final ovalWidth = size.width * 0.65;
    final ovalHeight = size.height * 0.55;

    // Outer semi-transparent vignette
    final backgroundPaint = Paint()..color = Colors.black.withOpacity(0.45);
    final backgroundPath = Path()
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height));

    final ovalRect = Rect.fromCenter(
      center: center,
      width: ovalWidth,
      height: ovalHeight,
    );

    final ovalPath = Path()..addOval(ovalRect);
    final transparentVignette = Path.combine(
      PathOperation.difference,
      backgroundPath,
      ovalPath,
    );
    canvas.drawPath(transparentVignette, backgroundPaint);

    // Oval Guide Border
    final borderPaint = Paint()
      ..color = isAligned ? BiomedicalTheme.accentGreen : BiomedicalTheme.accentTeal
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    canvas.drawOval(ovalRect, borderPaint);

    // Anatomical Zone indicators (Forehead & Cheeks subtle boxes)
    final roiPaint = Paint()
      ..color = (isAligned ? BiomedicalTheme.accentGreen : BiomedicalTheme.accentTeal).withOpacity(0.2)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;

    // Forehead box
    final fhRect = Rect.fromCenter(
      center: Offset(center.dx, center.dy - ovalHeight * 0.28),
      width: ovalWidth * 0.45,
      height: ovalHeight * 0.16,
    );
    canvas.drawRect(fhRect, roiPaint);

    // Left cheek
    final lcRect = Rect.fromCenter(
      center: Offset(center.dx - ovalWidth * 0.24, center.dy + ovalHeight * 0.08),
      width: ovalWidth * 0.24,
      height: ovalHeight * 0.16,
    );
    canvas.drawRect(lcRect, roiPaint);

    // Right cheek
    final rcRect = Rect.fromCenter(
      center: Offset(center.dx + ovalWidth * 0.24, center.dy + ovalHeight * 0.08),
      width: ovalWidth * 0.24,
      height: ovalHeight * 0.16,
    );
    canvas.drawRect(rcRect, roiPaint);
  }

  @override
  bool shouldRepaint(covariant FaceOverlayPainter oldDelegate) {
    return oldDelegate.isAligned != isAligned;
  }
}
